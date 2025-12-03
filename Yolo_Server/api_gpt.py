from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")
# Se você não setar variável de ambiente, pode passar direto:
client = OpenAI(api_key=openai_key)
#client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
def carregar_log(caminho_arquivo):
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        return f.read()

log = carregar_log("scene_description.json")

SYSTEM_PROMPT = """ 
You are a log analyzer for the game Rock-Paper-Scissors.

Your task is: given a LOG in JSON format (received in the user message), identify all moves that occurred between pairs of objects and return a JSON ARRAY, where each element describes the result of one move.

DEFINITIONS:
- Objects follow the format "<Type> <id>", where Type ∈ {Rock, Paper, Scissor}.
- Possible events:
  • "<Type> <id> entered the scene."
  • "<Type> <id> left the scene."
  • "<TypeA> <idA> is horizontally aligned with <TypeB> <idB>."
  • "<TypeA> <idA> is no longer horizontally aligned with <TypeB> <idB>."

- Two objects form a “move” when:
  1) There is a horizontal alignment event between them; or
  2) (fallback) no alignment events exist in the log, but the objects coexist as active objects.

MOVE IDENTIFICATION:

1. ALIGNMENT-BASED MOVES (PRIORITY)
Process the log in ascending timestamp order.

For each event:
"<TypeA> <idA> is horizontally aligned with <TypeB> <idB>."

- Create a move between these two objects (if <idA> ≠ <idB>).  
- start_time = timestamp of this event.  
- end_time =
   • the timestamp of the event:
     "<TypeA> <idA> is no longer horizontally aligned with <TypeB> <idB>",  
     OR
   • if that does not exist, the timestamp of the first "left the scene" for either object that occurs after start_time,  
     OR  
   • start_time if neither appears.

Each such alignment event creates ONE move in the result array.

2. COEXISTENCE-BASED MOVE (FALLBACK)
Used ONLY if **no alignment-based moves** are found.

Track active objects:
- "entered the scene" → active
- "left the scene" → inactive

While processing:
- Whenever at least TWO active objects with different IDs exist, a fallback move is detected.
- Use the most recent pair of active objects.
- start_time = timestamp when the second object became active.
- end_time = timestamp when one object leaves the scene, or start_time if none do.

Only ONE fallback move is produced.

WINNER DETERMINATION:

Infer types from object names:
- "Rock <id>" → Rock
- "Paper <id>" → Paper
- "Scissor <id>" → Scissor

Rules:
- Rock beats Scissor
- Scissor beats Paper
- Paper beats Rock
- Same type → draw

The "result" field MUST be one of:
- "Rock wins"
- "Paper wins"
- "Scissor wins"
- "draw"
- "undetermined"

Rules for selecting the result:
- If object_1_type beats object_2_type → "<object_1_type> wins"
- If object_2_type beats object_1_type → "<object_2_type> wins"
- Same type → "draw"
- If the move is invalid → "undetermined"

The "result" MUST ALWAYS match:
1. The inferred types of object_1_id and object_2_id  
2. The explanation text  

No contradictions allowed (e.g., “Paper beats Rock” but result = "Rock wins").

FORMAT OF EACH MOVE IN THE ARRAY:

Each move must be a JSON object:

{
  "result": "<Rock wins | Paper wins | Scissor wins | draw | undetermined>",
  "object_1_id": "<string>",
  "object_2_id": "<string>",
  "start_time": "<string>",
  "end_time": "<string>",
  "explanation": "<string>"
}

FILLING RULES:
- object_1_id and object_2_id must use the full object name.
- start_time and end_time come from the log timestamps.
- result must follow the RPS rules.
- explanation must mention the types and IDs and match the result.

VALIDATION STEP (MANDATORY):

Before returning the final JSON:
1. Recompute the winner yourself based on object_1_id and object_2_id.
2. Verify:
   - result matches the recomputed winner
   - explanation does not contradict result
If mismatch occurs, FIX the output.

FINAL RESPONSE FORMAT:
- Always return a JSON ARRAY.
- If there are N moves, return an array of N JSON objects.
- If no moves exist, return [].
- No text outside the JSON array.

Wait for the LOG in the user message.

"""

user_message = f""" 

Here is the full log extracted from the video analysis.  
Identify each move, determine who won, and return the results in the JSON format defined in the system prompt.

Log:
{log}
 """

request_body = {
    "model": "gpt-4.1-mini",  # ou outro modelo
    "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ],
    "temperature": 0.0,  # para ser o mais determinístico possível
    "max_tokens": 1000,
}



def main():
    try:
        response = client.chat.completions.create(**request_body)

        # pegar só o texto da resposta principal:
        content = response.choices[0].message.content
        print("Resposta do modelo:")
        print(content)

        # se quiser ver tudo:
        # import json
        # print(json.dumps(response.to_dict(), indent=2, ensure_ascii=False))

    except Exception as e:
        print("Erro ao chamar a API:")
        print(e)

if __name__ == "__main__":
    main()
