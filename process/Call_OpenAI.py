from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from classes.Events import Event

load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_key)


def convert_events_to_json(events):
    """
    Converte a lista de objetos Event em um JSON simples:
    [
      { "tInit": 0.00, "tEnd": 5.00, "name": "trabalhador 1 tempo em cena" }
    ]
    """
    converted = []

    for ev in events:
        converted.append({
            "tInit": round(ev.tInit, 2),
            "tEnd": round(ev.tEnd, 2),
            "name": ev.name
        })

    return converted


def build_payload(events):
    """
    Recebe a LISTA de Event() vindo do ListEvents(video)
    e monta o payload a ser enviado para a API.
    """

    # Converte lista de Event para JSON estruturado
    log_struct = convert_events_to_json(events)

    # Transformamos em string JSON bonitinha
    log_as_text = json.dumps(log_struct, indent=2, ensure_ascii=False)

    SYSTEM_PROMPT = """
    You are a safety log analyst.

    Goal: Given a JSON log of time-stamped events (Portuguese event names), decide for each worker if they wore required PPE (e.g., helmet/vest/gloves/eye protection) for most of their time in the scene. Use only the evidence in the log. Return a JSON array; no extra text.

    EVENT SCHEMA (names appear in Portuguese exactly as below):
    - "<obj> <id> tempo em cena" -> object existed from tInit to tEnd in that interval.
    - "<objA> <idA> alinhado com <objB> <idB>" -> centers horizontally aligned at that instant.
    - "<objA> <idA> deixou de alinhar com <objB> <idB>" -> alignment ended.
    - "<objA> <idA> sobrepos <objB> <idB>" -> bounding boxes overlap at that instant.
    - "<objA> <idA> deixou de sobrepor <objB> <idB>" -> overlap ended.
    - "Sinal vermelho saiu pelo topo (ID X)" -> red light object X disappeared (may be irrelevant for PPE).

    OBJECT NAMES:
    - Workers likely appear as "trabalhador <id>" (or similar human labels).
    - PPE items may appear as "capacete", "colete", "luva", "oculos", etc.

    INTERPRETATION RULES FOR PPE:
    1) A worker's time in scene is the duration from their "tempo em cena" event tInit to tEnd.
    2) Evidence that a worker is wearing/holding PPE is overlap or alignment events between the worker and a PPE object during that time window.
    3) If PPE evidence spans most (>50%) of the worker's time in scene, mark as wearing PPE. If clear lack for most of the time, mark as not wearing. Otherwise mark as inconclusive.
    4) Prefer overlap over mere alignment as stronger evidence that the PPE is being worn.
    5) If no PPE objects are present for that worker, default to "not wearing" unless the log is clearly incomplete, in which case "inconclusive".

    OUTPUT FORMAT:
    Return a JSON array; one object per worker, with:
    - "worker": string with worker name and id (e.g., "trabalhador 7").
    - "wearing_ppe_majority": true | false | "inconclusive".
    - "evidence": minimal list of event strings (from the log) that support the decision, ordered by time.
    - "notes": short justification (one sentence).

    No other text besides the JSON array.
    """

    user_message = f"""
    Here is the full event log extracted from the video analysis (JSON array).
    Decide for each worker whether they wore PPE for most of their time in the scene, following the rules above, and respond only with the JSON array in the required format.

    Log:
    {log_as_text}
    """
    print(log_as_text)
    return {
        "model": "gpt-4.1-mini",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.0,
        "max_tokens": 1000,
    }


def callOpenAI(events):
    """
    Recebe a LISTA de Event() produzida por ListEvents(video)
    """

    try:
        request_body = build_payload(events)
        response = client.chat.completions.create(**request_body)

        content = response.choices[0].message.content
        print("Resposta do modelo:")
        print(content)

    except Exception as e:
        print("Erro ao chamar a API:")
        print(e)


# Exemplo de uso com LISTA de Event():
if __name__ == "__main__":

    

    exemplo = [
        Event(0.00, 10.00, "trabalhador 1 tempo em cena"),
        Event(0.00, 8.00, "capacete 1 tempo em cena"),
        Event(0.50, 0.50, "trabalhador 1 sobrepos capacete 1"),
        Event(5.00, 5.00, "trabalhador 1 alinhado com capacete 1"),
    ]

    #callOpenAI(exemplo)
