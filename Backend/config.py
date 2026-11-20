import os
import requests
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LLM_MODEL = os.getenv("LM_STUDIO_MODEL", "qwen/qwen3-4b-2507")

response = requests.post(
  "http://localhost:1234/api/v1/chat",
  headers={
    "Authorization": f"Bearer {os.getenv('LM_API_TOKEN', '')}",
    "Content-Type": "application/json"
  },
  json={
    "model": LLM_MODEL,
    "input": "Write a short haiku about sunrise."
  }
)
print(json.dumps(response.json(), indent=2))

