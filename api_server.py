from linecache import cache

from PIL.features import check
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import requests
import whisper
import os
import re
import tempfile
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from speech.voicefox import generate_play_audio # Import Voicefox
from db_connect.db_connect import router as db_router, proses_pesan_utama, simpan_log_llm # Import module database
from memory_manager.memeory_Manage import extract_memory  
from memory_manager.save_memory import save_memory
from LLM.intent_classifier import classify_intent
from memory_manager.memory_cache import check_cache, get_response
from LLM.llm_config import LLM_URL, LLM_MODEL, get_headers, build_payload, clean_reply


app = FastAPI()

app.include_router(db_router)

print("[SISTEM] Memuat model Whisper, mohon tunggu...")
# device="cpu": VRAM 4 GB disisakan untuk GPT-SoVITS (suara) & LM Studio. Model "base" tetap cepat di CPU.
whisper_model = whisper.load_model("base", device="cpu")
print("[SISTEM] Model Whisper berhasil dimuat!")

# Frontend disajikan dari server yang sama (same-origin), jadi CORS hanya perlu untuk
# klien dari origin lain. Tambahkan origin lewat .env: ALLOWED_ORIGINS=https://a.com,https://b.com
ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PesanMasuk(BaseModel):
    chat: str
    number: int


# --- Audio balasan: satu file unik per jawaban ---
# Dulu semua jawaban menimpa voicefox_source/reply.wav, sehingga dua permintaan bersamaan
# (dua perangkat, atau chat + event) saling menimpa audionya.
REPLY_DIR = os.path.join("voicefox_source", "replies")
REPLY_MAX_AGE_SEC = 60 * 60      # file audio lebih tua dari 1 jam dihapus
os.makedirs(REPLY_DIR, exist_ok=True)

# Whisper tidak dijamin aman dipanggil paralel -> satu per satu.
whisper_lock = threading.Lock()

# TTS berjalan di LATAR BELAKANG lewat antrean satu pekerja:
# - teks balasan langsung dikirim ke frontend tanpa menunggu suara selesai dibuat;
# - audio dibuat satu per satu (GPT-SoVITS / VOICEVOX memang memproses berurutan),
#   sementara LLM sudah bisa mengerjakan chat berikutnya.
# Frontend mengambil audio lewat GET /api/audio/{audio_id} (menunggu sampai siap).
tts_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tts")
audio_jobs = {}                 # audio_id -> Future (path file atau None)
audio_jobs_lock = threading.Lock()
AUDIO_WAIT_TIMEOUT_SEC = 120


def _cleanup_old_replies():
    now = time.time()
    for name in os.listdir(REPLY_DIR):
        path = os.path.join(REPLY_DIR, name)
        try:
            if name.endswith(".wav") and now - os.path.getmtime(path) > REPLY_MAX_AGE_SEC:
                os.remove(path)
        except OSError:
            pass
    with audio_jobs_lock:
        for aid in [a for a, (f, t) in audio_jobs.items() if f.done() and now - t > REPLY_MAX_AGE_SEC]:
            del audio_jobs[aid]


def _buat_audio_file(teks: str, path: str):
    try:
        return generate_play_audio(teks, output_file=path)
    except Exception as e:
        print(f"[ERROR] Voicefox gagal: {e}")
        return None


def mulai_audio(teks: str):
    """Masukkan teks ke antrean TTS. Mengembalikan audio_id (bukan menunggu audionya)."""
    _cleanup_old_replies()
    audio_id = uuid.uuid4().hex
    future = tts_executor.submit(_buat_audio_file, teks, os.path.join(REPLY_DIR, f"{audio_id}.wav"))
    with audio_jobs_lock:
        audio_jobs[audio_id] = (future, time.time())
    return audio_id


def balasan_json(teks: str):
    """Format balasan ke frontend: teks sekarang, audio menyusul lewat `audio_wait`."""
    audio_id = mulai_audio(teks)
    return {"balasan": teks, "audio": None, "audio_id": audio_id, "audio_wait": f"/api/audio/{audio_id}"}


# Kalau LLM mengembalikan jawaban kosong (mis. hanya tag), coba lagi beberapa kali.
LLM_MAX_ATTEMPTS = int(os.getenv("LLM_MAX_ATTEMPTS", "3"))
FALLBACK_REPLY = "……ふ、ふん！なんでもないわよ。もう一回言ってみなさいよ、バカ。"

# Fungsi utama untuk memproses chat dari Teks -> LLM -> Voicefox
def proses_chat_llm(teks_user: str):
    print(f"\n[USER] Pesan masuk: {teks_user}")

    # --- 1. CEK INTENT KEUANGAN KE DATABASE DULU ---
    db_result = proses_pesan_utama(teks_user)
    if db_result.get("handled", False):
        balasan_ai = db_result["jawaban"]
        print(f"[SAKURA - DB] Membalas: {balasan_ai}")
        return balasan_json(balasan_ai)
    
    # --- 2. KONEKSI KE LM STUDIO (Qwen) ---
    # URL default dari Local Server LM Studio
    lm_studio_url = LLM_URL
    
    # Membentuk kepribadian AI (System Prompt) dengan membaca dari file .txt
    try:
        with open("source/system_prompt.txt", "r", encoding="utf-8") as file:
            system_prompt = file.read()
    except FileNotFoundError:
        system_prompt = "Kamu adalah Sakura, bicaralah menggunakan bahasa Jepang. Jawablah dengan singkat." # Fallback jika file hilang

    # Model diambil dari .env (LM_STUDIO_MODEL), default: qwen/qwen3-4b-2507
    payload = build_payload(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": teks_user}
        ],
        max_tokens=150   # Membatasi panjang teks agar responnya cepat
    )

    headers = get_headers()
    
    try:
        balasan_ai = ""
        for percobaan in range(1, LLM_MAX_ATTEMPTS + 1):
            # Mengirim pertanyaan ke LM Studio
            print(f"[SISTEM] Menunggu otak LLM (LM Studio / {LLM_MODEL}) berpikir... (percobaan {percobaan})")
            response = requests.post(lm_studio_url, headers=headers, json=payload, timeout=180)
            response_data = response.json()

            # Validasi format respons
            if not isinstance(response_data, dict) or 'choices' not in response_data:
                print(f"[ERROR] Respons tidak terduga dari LM Studio: {response_data}")
                return {"balasan": "Maaf, LM Studio mengembalikan respons yang tidak valid. Pastikan model sudah dimuat!"}

            # Mengekstrak teks balasan dari format OpenAI-compatible
            balasan_ai = clean_reply(response_data['choices'][0]['message']['content'])
            if balasan_ai:
                break
            print(f"[SISTEM] Balasan LLM kosong, mencoba lagi ({percobaan}/{LLM_MAX_ATTEMPTS})")
        else:
            balasan_ai = FALLBACK_REPLY
            print("[SISTEM] Balasan tetap kosong, memakai kalimat cadangan")
        print(f"[SAKURA] Membalas: {balasan_ai}")

        # Simpan obrolan LLM ke database
        simpan_log_llm(teks_user, balasan_ai)

        # --- AUDIO VIA VOICEFOX dibuat di latar belakang --- teks langsung dikirim ke HTML
        return balasan_json(balasan_ai)

    except Exception as e:
        print(f"[ERROR] Koneksi ke LM Studio gagal: {e}")
        return {"balasan": "Maaf, sepertinya koneksiku ke otak LLM sedang terputus. Pastikan Local Server di LM Studio sudah menyala ya!"}

# Catatan: rute sengaja memakai `def` (bukan `async def`). Isinya memanggil fungsi blocking
# (LM Studio, Whisper, TTS); dengan `def`, FastAPI menjalankannya di threadpool sehingga
# server tetap bisa melayani permintaan lain (dan nanti WebSocket) selama Sakura berpikir.
@app.post("/api/chat")
def chat_dengan_waifu(pesan: PesanMasuk):
    # Rute untuk chat via Teks biasa
    return proses_chat_llm(pesan.chat)

@app.get("/api/audio/{audio_id}")
def tunggu_audio(audio_id: str):
    """Tunggu sampai audio balasan selesai dibuat (maks. AUDIO_WAIT_TIMEOUT_SEC)."""
    if not re.fullmatch(r"[0-9a-f]{32}", audio_id):
        return {"ready": False, "url": None, "error": "audio_id tidak valid"}
    with audio_jobs_lock:
        job = audio_jobs.get(audio_id)
    if job is None:
        ada = os.path.exists(os.path.join(REPLY_DIR, f"{audio_id}.wav"))
        return {"ready": ada, "url": f"/audio/replies/{audio_id}.wav" if ada else None}
    try:
        path = job[0].result(timeout=AUDIO_WAIT_TIMEOUT_SEC)
    except FutureTimeout:
        return {"ready": False, "url": None, "error": "timeout"}
    return {"ready": bool(path), "url": f"/audio/replies/{audio_id}.wav" if path else None}

@app.post("/api/voice-chat")
def voice_chat_dengan_waifu(audio: UploadFile = File(...)):
    # Rute untuk chat via Suara (Microphone)
    print("\n[SISTEM] Menerima file audio dari frontend, sedang menganalisis...")
    
    # 1. Simpan audio sementara. Nama file dari browser TIDAK dipakai sebagai path
    #    (bisa berisi "../" -> menulis file di luar folder); cukup ambil ekstensinya.
    ext = os.path.splitext(audio.filename or "")[1].lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,5}", ext):
        ext = ".webm"
    temp_audio_path = os.path.join(tempfile.gettempdir(), f"sakura_voice_{uuid.uuid4().hex}{ext}")
    with open(temp_audio_path, "wb") as buffer:
        buffer.write(audio.file.read())
        
    # 2. Transcribe menggunakan Whisper
    try:
        print("[WHISPER] Mulai transkripsi...")
        with whisper_lock:
            result = whisper_model.transcribe(temp_audio_path, fp16=False)
        teks_user = result["text"].strip()
        print(f"[WHISPER] Hasil transkripsi: {teks_user}")
        
        # Hapus file audio sementara agar tidak menuhin memori
        os.remove(temp_audio_path)
        
        # 3. Lempar teks hasil transcribe ke fungsi chat biasa
        if not teks_user:
             return {"balasan": "Maaf, suaranya kurang jelas. Bisa diulangi?"}
             
        return proses_chat_llm(teks_user)
        
    except Exception as e:
        print(f"[ERROR] Whisper gagal: {e}")
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        return {"balasan": "Maaf, telingaku (Whisper) sedang bermasalah."}

# Memasang folder statis
app.mount("/Assets", StaticFiles(directory="Assets"), name="assets")
app.mount("/audio", StaticFiles(directory="voicefox_source"), name="audio")
app.mount("/Character", StaticFiles(directory="Character"), name="character")
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

if __name__ == "__main__":
    print("Server AI Menyala! Buka http://localhost:8080 di browser kamu.")
    uvicorn.run(app, host="127.0.0.1", port=8080)

def handle_user_iput(user_text):
    print(f"[SISTEM] Mengekstrak memori baru... ")
    extraccted_data = extract_memory(user_text)

    if extraccted_data:
        if isinstance(extraccted_data, list):
            save_memory(extraccted_data)
        elif isinstance(extraccted_data,dict):
            save_memory(extraccted_data)


def process_chat_llm ( teks_user: str): 
    intent, source = classify_intent(teks_user)
    print(f"[INTENT] {intent} | [Sumber] {source}")

    intent, source = classify_intent(teks_user, user_id="user01")
    print("[INTENT]", intent, source)

    cached_response = check_cache("user01", teks_user)
    if cached_response:
        return {"balasan": cached_response}
    