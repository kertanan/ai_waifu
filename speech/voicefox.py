import json
import os
import re
import time

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Mesin TTS: "sovits" (suara hasil training sendiri) atau "voicevox".
# Kalau "sovits" gagal (server belum jalan, dll), otomatis jatuh ke VOICEVOX.
TTS_ENGINE = os.getenv("TTS_ENGINE", "sovits").lower()

# --- GPT-SoVITS (api_v2.py) ---
SOVITS_URL = os.getenv("SOVITS_URL", "http://127.0.0.1:9880")
SOVITS_MODEL_DIR = os.getenv("SOVITS_MODEL_DIR", os.path.join("voice_model", "char001", "output"))
SOVITS_TEXT_LANG = os.getenv("SOVITS_TEXT_LANG", "ja")
# Kalau GPT-SoVITS gagal (mis. server tidak dinyalakan), lewati selama N detik dan langsung
# pakai VOICEVOX. Di Windows, koneksi ke port yang mati butuh ±2 detik sebelum gagal.
SOVITS_RETRY_SEC = float(os.getenv("SOVITS_RETRY_SEC", "60"))
_sovits_down_until = 0.0

# --- VOICEVOX ---
VOICEVOX_URL = os.getenv("VOICEVOX_URL", "http://127.0.0.1:50021")

OUTPUT_FILE = os.path.join(PROJECT_ROOT, "voicefox_source", "reply.wav")


# =========================
# TEXT PREPROCESSING
# =========================
def preprocess_text(text):

    # Hapus teks di dalam kurung (biasanya tag ekspresi seperti "(tersenyum)" atau "(marah)")
    # agar mesin TTS tidak ikut membacanya secara kaku.
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'（[^）]*）', '', text)
    text = re.sub(r'\[[^\]]*\]', '', text)
    text = re.sub(r'【[^】]*】', '', text)

    # natural punctuation
    text = text.replace("...", "…")

    # Spasi buatan tidak ditambahkan karena spasi dalam bahasa Jepang justru merusak intonasi alami

    # conversational tweak
    replacements = {
        "です。": "ですね。",
        "ます。": "ますね。",
        "はい。": "はい〜。",
        "わかりました": "わかりました〜",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text.strip()


def _save(audio_bytes, output_file=None):
    output_file = output_file or OUTPUT_FILE
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(audio_bytes)
    print(f"[VOICEFOX] Audio berhasil disimpan ke {output_file}")
    return output_file


# =========================
# GPT-SoVITS
# =========================
_sovits_model = None      # isi model_info.json + path absolut
_sovits_loaded = False    # bobot sudah dikirim ke server?


def _load_sovits_model():
    global _sovits_model
    if _sovits_model is None:
        model_dir = SOVITS_MODEL_DIR
        if not os.path.isabs(model_dir):
            model_dir = os.path.join(PROJECT_ROOT, model_dir)
        with open(os.path.join(model_dir, "model_info.json"), encoding="utf-8") as f:
            info = json.load(f)
        info["gpt_path"] = os.path.join(model_dir, info["gpt"])
        info["sovits_path"] = os.path.join(model_dir, info["sovits"])
        info["ref_audio_path"] = os.path.join(model_dir, info["ref_audio"])
        for key in ("gpt_path", "sovits_path", "ref_audio_path"):
            if not os.path.exists(info[key]):
                raise FileNotFoundError(f"File model tidak ditemukan: {info[key]}")
        _sovits_model = info
    return _sovits_model


def _ensure_sovits_weights(info):
    """Muat bobot GPT & SoVITS hasil training ke server api_v2 (sekali saja)."""
    global _sovits_loaded
    if _sovits_loaded:
        return
    for endpoint, path in (("set_gpt_weights", info["gpt_path"]),
                           ("set_sovits_weights", info["sovits_path"])):
        r = requests.get(f"{SOVITS_URL}/{endpoint}", params={"weights_path": path}, timeout=120)
        if r.status_code != 200:
            raise RuntimeError(f"{endpoint} gagal ({r.status_code}): {r.text[:200]}")
    print(f"[VOICEFOX] Model '{info['speaker']}' dimuat ke GPT-SoVITS")
    _sovits_loaded = True


def generate_sovits(text, speed=1.0, temperature=1.0, top_k=15, top_p=1.0, output_file=None):
    global _sovits_loaded
    info = _load_sovits_model()
    _ensure_sovits_weights(info)

    payload = {
        "text": text,
        "text_lang": SOVITS_TEXT_LANG,
        "ref_audio_path": info["ref_audio_path"],
        "prompt_text": info["ref_text"],
        "prompt_lang": info.get("ref_lang", "ja"),
        "text_split_method": "cut5",   # potong per tanda baca
        "batch_size": 1,
        "media_type": "wav",
        "streaming_mode": False,
        "speed_factor": speed,
        "temperature": temperature,
        "top_k": top_k,
        "top_p": top_p,
    }
    r = requests.post(f"{SOVITS_URL}/tts", json=payload, timeout=300)
    if r.status_code != 200:
        # server mungkin di-restart -> bobot perlu dimuat ulang di panggilan berikutnya
        _sovits_loaded = False
        raise RuntimeError(f"/tts gagal ({r.status_code}): {r.text[:300]}")
    return _save(r.content, output_file)


# =========================
# VOICEVOX
# =========================
def generate_voicevox(text, speed=1.0, pitch=0.0, speaker_jp=14, intonation=1.0, volume=1.0, output_file=None):
    response_query = requests.post(
        f"{VOICEVOX_URL}/audio_query",
        params={"text": text, "speaker": speaker_jp},
        timeout=60,
    )
    if response_query.status_code != 200:
        print(f"[VOICEFOX] Error audio_query: {response_query.status_code}")
        return

    blueprint_voice = response_query.json()
    blueprint_voice["speedScale"] = speed
    blueprint_voice["pitchScale"] = pitch
    blueprint_voice["intonationScale"] = intonation
    blueprint_voice["volumeScale"] = volume

    response_synthesis = requests.post(
        f"{VOICEVOX_URL}/synthesis",
        params={"speaker": speaker_jp},
        json=blueprint_voice,
        timeout=120,
    )
    if response_synthesis.status_code != 200:
        print(f"[VOICEFOX] Error synthesis: {response_synthesis.status_code}")
        return

    return _save(response_synthesis.content, output_file)


# =========================
# GENERATE AUDIO
# =========================
def generate_play_audio(
    text,
    voice="sakura",
    speed=1.0,
    pitch=0.0,
    speaker_jp=14,   # ID VOICEVOX (dipakai kalau engine = voicevox / fallback); 14 = Meimei Himari
    intonation=1.0,
    volume=1.0,
    output_file=None,   # None = voicefox_source/reply.wav (perilaku lama)
):
    """Buat audio dari teks. Mengembalikan path file audio, atau None kalau gagal."""

    processed_text = preprocess_text(text)
    if not processed_text:
        print("[VOICEFOX] Teks kosong setelah dibersihkan, tidak ada audio dibuat")
        return

    print(f"[VOICEFOX] ({TTS_ENGINE}) memproses suara '{processed_text}' (speed={speed})")

    global _sovits_down_until, _sovits_loaded
    if TTS_ENGINE == "sovits" and time.time() >= _sovits_down_until:
        try:
            return generate_sovits(processed_text, speed=speed, output_file=output_file)
        except (requests.exceptions.RequestException, RuntimeError, FileNotFoundError, KeyError) as e:
            # Server SoVITS bisa saja di-restart: muat ulang bobot char001 di percobaan berikutnya,
            # kalau tidak, server baru memakai suara bawaan.
            _sovits_loaded = False
            _sovits_down_until = time.time() + SOVITS_RETRY_SEC
            print(f"[VOICEFOX] GPT-SoVITS gagal ({e}), beralih ke VOICEVOX "
                  f"(SoVITS dilewati {SOVITS_RETRY_SEC:.0f} dtk)")

    try:
        return generate_voicevox(processed_text, speed=speed, pitch=pitch, speaker_jp=speaker_jp,
                                 intonation=intonation, volume=volume, output_file=output_file)
    except requests.exceptions.RequestException as e:
        print(f"[VOICEFOX] Error koneksi VOICEVOX: {e}")
        return


if __name__ == "__main__":

    teks_tes = """
    えっと〜…
    システム起動完了です。
    今日もよろしくお願いしますね、マスター。
    """

    generate_play_audio(teks_tes, speed=0.95)
