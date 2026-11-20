import re
import sqlite3
import json
import logging
import requests
from rapidfuzz import fuzz, process
from LLM.intent_classifier import save_cache
from LLM.llm_config import LLM_URL, LLM_MODEL, get_headers, clean_reply


def normalize_text(text: str) -> str: 
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = " ".join(text.split())
    return text


def similarity_check(text1: str, text2: str, threshold: int = 80) -> dict:
    """
    Compare two strings and return a normalized similarity score.

    Returns:
        {
            "is_similar": bool,
            "score": int,
            "normalized_text1": str,
            "normalized_text2": str
        }
    """
    normalized_text1 = normalize_text(text1)
    normalized_text2 = normalize_text(text2)

    score = fuzz.ratio(normalized_text1, normalized_text2)
    return {
        "is_similar": score >= threshold,
        "score": score,
        "normalized_text1": normalized_text1,
        "normalized_text2": normalized_text2,
    }


def find_best_similarity(query: str, candidates: list[str], threshold: int = 80):
    """
    Find the most similar candidate from a list of strings.
    This is useful when exact cache key matching fails.
    """
    if not candidates:
        return None

    normalized_query = normalize_text(query)
    normalized_candidates = [normalize_text(candidate) for candidate in candidates]
    best_match = process.extractOne(normalized_query, normalized_candidates)

    if best_match is None:
        return None

    candidate_text, score, _index = best_match
    return {
        "candidate": candidate_text,
        "score": score,
        "is_similar": score >= threshold,
    }


def check_cache(user_id: str, user_text: str, message: str = ""):
    normalized = normalize_text(user_text)
    key = f"{user_id}:{normalized}"

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
            "SELECT value FROM memory WHERE key = ?", (key,)
    )
    row = cursor.fetchone()

    conn.close()
    return row[0]if row else None 

#create a function to hit or miss the cache if miss connect to the LLM Studio API and get the response and save it to the cache
def get_response (User_id: str, user_text: str, message: str): 
    cached_response = check_cache(User_id,user_text,message)

    if cached_response: 
        logging.info(f"[CACHE HIT] User: {User_id} | Text: {user_text} | Response: {cached_response}")
        return cached_response
    else: 

        logging.info(f"[CACHE MISS] User: {User_id} | Text: {user_text} | Fetching from LLM Studio API")
        response = fetch_from_llm_studio(user_text)
        if response:
            save_cache(User_id, user_text, response)
            return response
        else:
            logging.error(f"[LLM STUDIO ERROR] Failed to fetch response for User: {User_id} | Text: {user_text}")
            return None


#return the response from the LLM Studio API
def fetch_from_llm_studio (User_text:  str): 
    LLM_STUDIO_URL = LLM_URL
    system_prompt = open (
        "source/system_prompt.txt", "r", encoding="utf-8"
    ).read()

    payload = {
        "model": LLM_MODEL,
        "messages":[
            {"role" : "system", "content": system_prompt},
            {"role" : "user", "content": User_text},
        ],
        "temperature": 0
    }

    try:
        r = requests.post(
            LLM_STUDIO_URL,
            json = payload,
            headers = get_headers()
        )
        r.raise_for_status()
        text = clean_reply(r.json()["choices"][0]["message"]["content"])
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except requests.exceptions.RequestException as e:
        logging.error(f"[LLM STUDIO ERROR] Request failed: {e}")
        return None
    except (KeyError, json.JSONDecodeError) as e:
        logging.error(f"[LLM STUDIO ERROR] Failed to parse response: {e}")
        return None