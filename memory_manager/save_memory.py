import sqlite3

from langchain_community import memory

def save_memory(memory):
    if not memory or not isinstance(memory, dict):
        return
    required_keys = ["category", "key", "value", "importance"]
    for k in required_keys:
        if k not in memory:
            print(f"[MEMORY ERROR] Format JSON tidak lengkap. Kehilangan key: {k}")
            return
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

    # Membuat tabel memory jika belum ada
        cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                key TEXT,
                value TEXT,
                importance INTEGER
                 )
             """)
        cursor.execute("""
            INSERT INTO memory (category, key, value, importance) 
            VALUES (?, ?, ?, ?)
        """, (memory["category"], memory["key"], memory["value"], memory["importance"]))
    
        conn.commit()
        print(f"[MEMORY SAVED] Tersimpan: {memory['key']} -> {memory['value']}")
    except sqlite3.Error as e:
        print(f"[MEMORY ERROR] Gagal menyimpan memory: {e}")
    finally:
        if conn:
            conn.close()