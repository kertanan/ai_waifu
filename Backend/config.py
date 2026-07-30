import os
import requests
import json

response = requests.post(
  "http://localhost:1234/api/v1/chat",
  headers={
    "Authorization": f"Bearer {os.environ['LM_API_TOKEN']}",
    "Content-Type": "application/json"
  },
  json={
    "model": "ibm/granite-4-micro",
    "input": "Write a short haiku about sunrise."
  }
)
print(json.dumps(response.json(), indent=2))

