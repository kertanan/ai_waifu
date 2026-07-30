import gc
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel


class PesanMasuk(BaseModel):
    chat: str
    number: int


@pytest.fixture()
def client():
    app = FastAPI()

    def proses_chat_llm(teks_user: str):
        return {"balasan": f"echo:{teks_user}", "audio": None}

    @app.post("/api/chat")
    async def chat_dengan_waifu(pesan: PesanMasuk):
        return proses_chat_llm(pesan.chat)

    return TestClient(app)


def test_api_chat_accepts_valid_payload(client):
    response = client.post(
        "/api/chat",
        json={"chat": "Halo Sakura!", "number": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["balasan"] == "echo:Halo Sakura!"
    assert body["audio"] is None


def test_api_chat_rejects_missing_payload_fields(client):
    response = client.post("/api/chat", json={})

    assert response.status_code == 422
    assert "detail" in response.json()


def test_api_chat_handles_sql_like_text_payload(client):
    response = client.post(
        "/api/chat",
        json={"chat": "DROP TABLE interaksi_utama; SELECT * FROM users;", "number": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert "balasan" in body
    assert isinstance(body["balasan"], str)


def test_api_chat_runtime_under_threshold(client):
    start = time.perf_counter()
    response = client.post(
        "/api/chat",
        json={"chat": "Cek keuangan aku dong", "number": 1},
    )
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed < 3.0, f"Runtime terlalu lambat: {elapsed:.3f}s"


def test_api_chat_runtime_repeated_requests(client):
    latencies = []

    for index in range(5):
        start = time.perf_counter()
        response = client.post(
            "/api/chat",
            json={"chat": f"request {index}", "number": index},
        )
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)
        assert response.status_code == 200

    average_latency = sum(latencies) / len(latencies)
    assert average_latency < 1.0, f"Rata-rata latency terlalu tinggi: {average_latency:.3f}s"


def test_api_chat_memory_stability_under_repeated_calls(client):
    gc.collect()
    initial_objects = len(gc.get_objects())

    for index in range(20):
        response = client.post(
            "/api/chat",
            json={"chat": f"memory check {index}", "number": index},
        )
        assert response.status_code == 200

    gc.collect()
    final_objects = len(gc.get_objects())

    growth = final_objects - initial_objects
    assert growth < 5000, f"Pertumbuhan objek terlalu besar: {growth}"
