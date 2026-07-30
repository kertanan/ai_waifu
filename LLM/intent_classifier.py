import re
import sqlite3
from typing import Dict, Optional, Tuple

INTENT_RULES : Dict[str, list[str]] ={
    "greeting": [r"\b(hi|hello|halo|hey|selamat pagi|selamat siang|selamat sore|pagi|siang|sore)\b"],
    "ask_identity": [r"\b(siapa|nama|identitas|kamu|anda)\b"],
    "ask_waifu" :  [r"\b(waifu|anime|character|karakter|couple|pasangan)\b"],
    "farewell" : [r"\b(bye|goodbye|selamat tinggal|sampai jumpa|dadah|see you)\b"],
    "emotion": [r"\b(sedih|senang|bahagia|marah|stress|bosan|gembira|kesal|sedikit)\b"],
    "request": [r"\b(tolong|bantu|help|please|minta|tolong bantu)\b"],
    "question": [r"\b(apa|bagaimana|mengapa|kapan|siapa|di mana|where|how|why|when)\b"],
}
def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.strip().lower()
    text = re.sub(r"\s+"," ", text)
    return text

def build_cache_key ( user_id : str, message : str) -> str:
    normalized_message = normalize_text(message)
    return f"{user_id}:{normalized_message}"

def connect_db(db_path: str = "database.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def check_cache (user_id: str, message: str, db_connection : str = "database.db") -> Optional[str]:
    cache_key = build_cache_key(user_id, message)

    conn = connect_db(db_connection)
    try : 
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM memory WHERE key = ?", (cache_key,))
        row = cursor.fetchone()
        return dict (row) ["value"] if row is not None else None
    except sqlite3.Error as e:
        print(f"Error occurred while checking cache: {e}")
        return None
    finally: 
        conn.close()

def save_cache (user_id: str, message:str , intent : str , db_path : str = "database.db") -> bool:
    cache_key = build_cache_key(user_id, message)

    conn = connect_db(db_path)
    try :
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                key TEXT UNIQUE,
                value TEXT,
                importance INTEGER
            )
        """)
        cursor.execute(
            """
            INSERT INTO memory (category, key, value, importance)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            ("intent", cache_key, intent, 1),
        )
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error occurred while saving to cache: {e}")
        return False
    finally:
        conn.close()


def classify_intent(
    message: str,
    user_id: str = "anonymous",
    use_cache: bool = True
) -> Tuple[str, str]:
    """
    Returns:
        (intent_name, source)
    """

    normalized_message = normalize_text(message)

    # Check cache
    if use_cache:
        cached_intent = check_cache(user_id, normalized_message)
        if cached_intent:
            return cached_intent, "cache"

    # Rule-based scoring
    scores: Dict[str, int] = {intent: 0 for intent in INTENT_RULES}

    for intent, patterns in INTENT_RULES.items():
        if any(re.search(pattern, normalized_message) for pattern in patterns):
            scores[intent] += 1

    best_intent = max(scores, key=scores.get)

    if scores[best_intent] == 0:
        best_intent = "unknown"

    if use_cache:
        save_cache(user_id, normalized_message, best_intent)

    return best_intent, "rule"

