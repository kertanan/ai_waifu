import sqlite3
import requests

print("=== MENGIRIM PESAN KE SERVER ===")
url = "http://localhost:8080/api/chat_db"
payload = {"teks": "aku baru aja jajan boba harganya mahal banget"}

try:
    response = requests.post(url, json=payload)
    print("Respon dari Sakura:", response.json())
except Exception as e:
    print("Gagal menghubungi server:", e)

print("\n=== MENGECEK ISI DATABASE ===")
try:
    db = sqlite3.connect("database.db")
    cursor = db.cursor()

    print("\n1. Isi Tabel 'interaksi_utama':")
    for row in cursor.execute("SELECT * FROM interaksi_utama").fetchall():
        print("  ->", row)

    print("\n2. Isi Tabel 'log_obrolan':")
    for row in cursor.execute("SELECT * FROM log_obrolan").fetchall():
        print("  ->", row)

    print("\n3. Isi Tabel 'data_keuangan':")
    for row in cursor.execute("SELECT * FROM data_keuangan").fetchall():
        print("  ->", row)
except Exception as e:
    print("Gagal membaca database:", e)
