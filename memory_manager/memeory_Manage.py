import requests
import json

from rich import text

from LLM.llm_config import LLM_URL as LLM_STUDIO_URL, LLM_MODEL, get_headers, clean_reply

def extract_memory(user_text):

    system_prompt = open (
        "source/system_prompt.txt", "r", encoding="utf-8"
    ).read()

    payload = {
        "model": LLM_MODEL,
        "messages":[
            {"role" : "system", "content": system_prompt},
            {"role" : "user", "content": user_text},
        ],
        "temperature": 0
    }

    r = requests.post(
        LLM_STUDIO_URL,
        json = payload,
        headers = get_headers()
    )

    text = clean_reply(r.json()["choices"][0]["message"]["content"])
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]

    return json.loads(text.strip())
