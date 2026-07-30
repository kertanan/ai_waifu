import requests
import json

from rich import text

LLM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"  

def extract_memory(user_text):

    system_prompt = open (
        "source/system_prompt.txt", "r", encoding="utf-8"
    ).read()

    payload = {
        "model": "ibm/granite-4-micro",
        "messages":[
            {"role" : "system", "content": system_prompt},
            {"role" : "user", "content": user_text},
            {"role" : "assistant", "content": ""}
        ],
        "temperature": 0
    }

    r = requests.post(
        LLM_STUDIO_URL,
        json = payload
    )

    text = r.json()["choices"][0]["message"]["content"]

    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]

    return json.loads(text.strip())
