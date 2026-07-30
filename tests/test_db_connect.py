import os
import sys
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import db_connect.db_connect as db_module
from db_connect.db_connect import (
    deteksi_intent,
    extract_data_keuangan,
    cek_keuangan,
    proses_pesan_utama,
)


@pytest.fixture
def db_cleanup():
    conn = sqlite3.connect("database_test.db")
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS log_obrolan")
    cursor.execute("DROP TABLE IF EXISTS data_keuangan")
    cursor.execute("DROP TABLE IF EXISTS interaksi_utama")
    conn.commit()
    conn.close()

    import db_connect.db_connect as db_module
    db_module.db.close()
    db_module.db = sqlite3.connect("database_test.db", check_same_thread=False)
    db_module.cursor = db_module.db.cursor()
    db_module.create_tables()

    yield

    db_module.db.close()
    if os.path.exists("database_test.db"):
        os.remove("database_test.db")


def test_deteksi_intent_keuangan_keluar():
    assert deteksi_intent("Saya habis beli makan 50000") == "keuangan_keluar"


def test_deteksi_intent_keuangan_masuk():
    assert deteksi_intent("Saya dapat uang 100000") == "keuangan_masuk"


def test_deteksi_intent_cek_keuangan():
    assert deteksi_intent("Cek sisa uang saya") == "cek_keuangan"


def test_extract_data_keuangan_angka_terakhir():
    data = extract_data_keuangan("Saya beli kopi 2 gelas seharga 5000 dan snack 3000")
    assert data["jumlah"] == 3000.0
    assert data["kategori"] == "umum"


def test_cek_keuangan_kosong(db_cleanup):
    assert cek_keuangan() == "0"


def test_proses_pesan_utama_keuangan_keluar(db_cleanup):
    result = proses_pesan_utama("Saya beli makan 50000")
    assert result["handled"] is True
    assert result["intent"] == "keuangan_keluar"
    assert "50000" in result["jawaban"]


def test_proses_pesan_utama_cek_keuangan(db_cleanup):
    proses_pesan_utama("Saya dapat uang 100000")
    result = proses_pesan_utama("cek sisa uang saya")
    assert result["handled"] is True
    assert result["intent"] == "cek_keuangan"
    assert "100000" in result["jawaban"] or "0" in result["jawaban"]


def test_chat_db_endpoint(db_cleanup):
    app = FastAPI()
    app.include_router(db_module.router)
    client = TestClient(app)

    response = client.post("/api/chat_db", json={"teks": "Saya beli kopi 5000"})

    assert response.status_code == 200
    assert response.json()["status"] == "sukses"
    assert response.json()["intent"] == "keuangan_keluar"
