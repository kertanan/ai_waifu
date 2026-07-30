import os
import sys

sys.path.insert(0, os.getcwd())

from fastapi.testclient import TestClient
import api_server

client = TestClient(api_server.app)

payloads = [
    ({'chat': 'Halo Sakura!', 'number': 1}, 'valid_text'),
    ({}, 'empty_payload'),
    ({'chat': 'DROP TABLE interaksi_utama;', 'number': 1}, 'injection_text'),
    ({'chat': 'aku baru aja jajan boba 25000', 'number': 1}, 'financial_intent'),
]

for payload, label in payloads:
    try:
        response = client.post('/api/chat', json=payload)
        print(label, response.status_code, response.text[:400])
    except Exception as exc:
        print(label, 'ERROR', exc)
