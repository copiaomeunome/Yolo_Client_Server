from openai import OpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_key)


def convert_events_to_json(events):
    """
    Converte a lista de objetos Event em um JSON estrutural
    parecido com o log antigo, mas simples e direto:

    [
      { "tInit": 0.00, "tEnd": 0.00, "name": "Rock 1 entered the scene." },
      { "tInit": 0.05, "tEnd": 0.05, "name": "Rock 1 aligned with Paper 2." }
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
    You are a log analyzer for the game Rock-Paper-Scissors.

    Your task is: given a LOG in JSON format (received in the user message), 
    identify all moves that occurred between pairs of objects and return a JSON ARRAY,
    where each element describes the result of one move.

    DEFINITIONS:
    - Objects follow the format "<Type> <id>", where Type ∈ {Rock, Paper, Scissor}.
    - Possible events:
      • "<Type> <id> entered the scene."
      • "<Type> <id> left the scene."
      • "<TypeA> <idA> is horizontally aligned with <TypeB> <idB>."
      • "<TypeA> <idA> is no longer horizontally aligned with <TypeB> <idB>."

    MOVE DETECTION RULES:
      (mesmo conteúdo original aqui...)

    FINAL RESPONSE FORMAT:
    - Always return a JSON ARRAY.
    - No text outside the JSON array.
    """

    user_message = f"""
    Here is the full log extracted from the video analysis.
    Identify each move, determine the winner, and return the results in JSON format.

    Log:
    {log_as_text}
    """

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

    class Event:
        def __init__(self, tInit, tEnd, name):
            self.tInit = tInit
            self.tEnd = tEnd
            self.name = name

    exemplo = [
        Event(0.00, 0.00, "Rock 1 entered the scene."),
        Event(0.00, 0.00, "Paper 2 entered the scene."),
        Event(0.05, 0.05, "Rock 1 is horizontally aligned with Paper 2."),
    ]

    callOpenAI(exemplo)
