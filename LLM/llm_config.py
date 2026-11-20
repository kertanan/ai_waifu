"""
Konfigurasi LLM terpusat (LM Studio, OpenAI-compatible API).

Semua modul yang memanggil LLM mengambil URL, nama model, dan header dari sini,
sehingga ganti model cukup lewat .env (LM_STUDIO_MODEL) tanpa mengubah kode.
"""
import os
import re

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LLM_URL = os.getenv("LM_STUDIO_URL", "http://127.0.0.1:1234/v1/chat/completions")
LLM_MODEL = os.getenv("LM_STUDIO_MODEL", "qwen/qwen3-4b-2507")
LLM_API_TOKEN = os.getenv("LM_API_TOKEN", "")

# Parameter sampling yang direkomendasikan untuk Qwen3-4B-Instruct-2507
QWEN_SAMPLING = {
    "temperature": 0.7,
    "top_p": 0.8,
    "top_k": 20,
    "min_p": 0.0,
}


def get_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if LLM_API_TOKEN and LLM_API_TOKEN != "your-api-token-here":
        headers["Authorization"] = f"Bearer {LLM_API_TOKEN}"
    return headers


def build_payload(messages: list, **overrides) -> dict:
    """Membuat payload chat/completions dengan model & sampling default Qwen."""
    payload = {"model": LLM_MODEL, "messages": messages, **QWEN_SAMPLING}
    payload.update(overrides)
    return payload


_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
# Model fine-tune Sakura (sakura-qwen3-4b) kadang mengawali jawaban dengan tag
# <tool_call>/</tool_call> kosong (sisa blok <think></think> kosong saat training).
_STRAY_TAG_RE = re.compile(r"</?(?:tool_call|think)>")


def clean_reply(text: str) -> str:
    """Buang blok <think>...</think> dan tag sisa agar tidak ikut dibacakan TTS."""
    text = _THINK_RE.sub("", text or "")
    return _STRAY_TAG_RE.sub("", text).strip()
