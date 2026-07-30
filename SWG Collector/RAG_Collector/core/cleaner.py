import re
import unicodedata
from typing import Any, Dict, List, Optional


def remove_html_tags(text: str) -> str:
    clean = re.sub(r"<[^>]+>", "", text)
    clean = re.sub(r"&nbsp;", " ", clean)
    clean = re.sub(r"&amp;", "&", clean)
    clean = re.sub(r"&lt;", "<", clean)
    clean = re.sub(r"&gt;", ">", clean)
    clean = re.sub(r"&quot;", '"', clean)
    clean = re.sub(r"&#39;", "'", clean)
    return clean


def remove_markdown(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    text = re.sub(r"~~([^~]+)~~", r"\1", text)
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^>\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\|.*\|$", "", text, flags=re.MULTILINE)
    return text


def normalize_whitespace(text: str) -> str:
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" +", " ", text)
    return text.strip()


def normalize_newlines(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def normalize_unicode(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u200b", "")
    text = text.replace("\ufeff", "")
    return text


def remove_code_blocks(text: str) -> str:
    text = re.sub(r"```[\s\S]*?```", "[CODE]", text)
    text = re.sub(r"`[^`]+`", "[CODE]", text)
    return text


def extract_code_blocks(text: str) -> List[str]:
    code_blocks = re.findall(r"```(?:\w+)?\n?([\s\S]*?)```", text)
    inline_codes = re.findall(r"`([^`]+)`", text)
    return code_blocks + inline_codes


def clean_text(
    text: str,
    remove_html: bool = True,
    remove_md: bool = True,
    normalize_ws: bool = True,
    normalize_nl: bool = True,
    normalize_uni: bool = True,
) -> str:
    if not text:
        return ""

    if remove_html:
        text = remove_html_tags(text)
    if remove_md:
        text = remove_markdown(text)
    if normalize_uni:
        text = normalize_unicode(text)
    if normalize_nl:
        text = normalize_newlines(text)
    if normalize_ws:
        text = normalize_whitespace(text)

    return text


def clean_document(
    document: Dict[str, Any],
    text_fields: Optional[List[str]] = None,
    **kwargs,
) -> Dict[str, Any]:
    if text_fields is None:
        text_fields = ["problem", "solution", "title", "code"]

    cleaned = document.copy()

    for field in text_fields:
        if field in cleaned and isinstance(cleaned[field], str):
            cleaned[field] = clean_text(cleaned[field], **kwargs)

    if "tags" in cleaned and isinstance(cleaned["tags"], list):
        cleaned["tags"] = [
            clean_text(tag, remove_html=False, remove_md=False).strip().lower()
            for tag in cleaned["tags"]
            if isinstance(tag, str)
        ]
        cleaned["tags"] = [t for t in cleaned["tags"] if t]

    return cleaned


def clean_documents(
    documents: List[Dict[str, Any]],
    text_fields: Optional[List[str]] = None,
    **kwargs,
) -> List[Dict[str, Any]]:
    return [clean_document(doc, text_fields, **kwargs) for doc in documents]


def remove_empty_fields(document: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in document.items() if v is not None and v != "" and v != []}


def truncate_text(text: str, max_length: int = 10000, suffix: str = "...") -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix
