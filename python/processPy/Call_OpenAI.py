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
    Voce e um analista de transito.

    Objetivo: Dado um log JSON de eventos (nomes em portugues), decidir para cada veiculo se ele atravessou um sinal vermelho. Use apenas as evidencias no log. Sempre responda somente com um array JSON; nenhum texto extra.

    EVENTOS IMPORTANTES (nomes aparecem exatamente como no log):
    - "<obj> <id> tempo em cena" -> objeto esteve presente de tInit ate tEnd.
    - "<objA> <idA> tempo de alinhamento com <objB> <idB>" ou "tempo de sobreposicao" -> centro alinhado ou caixas sobrepostas entre os objetos.
    - "Sinal vermelho saiu pelo topo (ID X)" -> o semaforo vermelho X desapareceu pelo topo do quadro; use como evidencia de que o sinal vermelho foi ultrapassado naquele momento.

    REGRAS DE INTERPRETACAO:
    1) Veiculos costumam aparecer como "carro", "car", "veiculo" (ou similares) seguidos de um id.
    2) Se um veiculo esta em cena quando ocorre "Sinal vermelho saiu pelo topo", considere forte evidencia de que ele avancou o sinal. Se o veiculo surge imediatamente antes e permanece enquanto o evento ocorre, trate como violacao.
    3) Se o veiculo entra apenas depois que o vermelho ja saiu ha algum tempo, marque como "inconclusivo" (nao e possivel afirmar).
    4) Caso nao haja qualquer evento de vermelho, devolva "inconclusivo" para todos.
    5) Sempre liste as evidencias como as strings de evento originais, em ordem cronologica, e use "inconclusivo" quando faltarem dados claros.

    FORMATO DE SAIDA (array JSON):
    - "veiculo": nome/id do veiculo (ex.: "carro 3").
    - "passou_sinal_vermelho": true | false | "inconclusivo".
    - "evidencias": lista minima de strings do log que sustentam a conclusao, em ordem temporal.
    - "notas": justificativa curta em uma frase.

    Nenhum outro texto alem do array JSON.
    """

    user_message = f"""
    Aqui esta o log de eventos extraido do video (array JSON).
    Decida, seguindo as regras acima, se algum veiculo avancou o sinal vermelho e responda somente com o array JSON.

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
