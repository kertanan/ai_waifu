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
from speech.voicefox import generate_play_audio # Import Voicefox
from db_connect.db_connect import router as db_router, proses_pesan_utama, simpan_log_llm # Import module database
from memory_manager.memeory_Manage import extract_memory  
from memory_manager.save_memory import save_memory
from LLM.intent_classifier import classify_intent
from memory_manager.memory_cache import check_cache, get_response


app = FastAPI()

app.include_router(db_router)

print("[SISTEM] Memuat model Whisper, mohon tunggu...")
whisper_model = whisper.load_model("base") # Menggunakan base agar lebih cepat di CPU, bisa diganti ke "turbo" jika kuat
print("[SISTEM] Model Whisper berhasil dimuat!")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PesanMasuk(BaseModel):
    chat: str
    number: int

# Fungsi utama untuk memproses chat dari Teks -> LLM -> Voicefox
def proses_chat_llm(teks_user: str):
    print(f"\n[USER] Pesan masuk: {teks_user}")
    
    # --- 1. CEK INTENT KEUANGAN KE DATABASE DULU ---
    db_result = proses_pesan_utama(teks_user)
    if db_result.get("handled", False):
        balasan_ai = db_result["jawaban"]
        print(f"[SAKURA - DB] Membalas: {balasan_ai}")
        
        try:
            generate_play_audio(balasan_ai)
            audio_url = "/audio/reply.wav"
        except Exception as e:
            print(f"[ERROR] Voicefox gagal: {e}")
            audio_url = None
            
        return {"balasan": balasan_ai, "audio": audio_url}
    
    # --- 2. KONEKSI KE LM STUDIO (Granite) ---
    # URL default dari Local Server LM Studio
    lm_studio_url = "http://127.0.0.1:1234/v1/chat/completions"
    
    # Membentuk kepribadian AI (System Prompt) dengan membaca dari file .txt
    try:
        with open("source/system_prompt.txt", "r", encoding="utf-8") as file:
            system_prompt = file.read()
    except FileNotFoundError:
        system_prompt = "Kamu adalah Sakura, bicaralah menggunakan bahasa Jepang. Jawablah dengan singkat." # Fallback jika file hilang

    payload = {
        "model": "granite", # Model Granite di LM Studio
        "messages": [
            {
                "role": "system", 
                "content": system_prompt
            },
            {"role": "user", "content": teks_user}
        ],
        "temperature": 0.7, # Tingkat kreativitas jawaban
        "max_tokens": 150   # Membatasi panjang teks agar responnya cepat
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        # Mengirim pertanyaan ke LM Studio
        print("[SISTEM] Menunggu otak LLM (LM Studio / Granite) berpikir...")
        response = requests.post(lm_studio_url, headers=headers, json=payload)
        response_data = response.json()
        
        # Validasi format respons
        if not isinstance(response_data, dict) or 'choices' not in response_data:
            print(f"[ERROR] Respons tidak terduga dari LM Studio: {response_data}")
            return {"balasan": "Maaf, LM Studio mengembalikan respons yang tidak valid. Pastikan model sudah dimuat!"}
        
        # Mengekstrak teks balasan dari format OpenAI-compatible
        balasan_ai = response_data['choices'][0]['message']['content']
        print(f"[SAKURA] Membalas: {balasan_ai}")
        
        # Simpan obrolan LLM ke database
        simpan_log_llm(teks_user, balasan_ai)
        
        # --- GENERATE AUDIO VIA VOICEFOX ---
        try:
            generate_play_audio(balasan_ai)
            audio_url = "/audio/reply.wav"
        except Exception as e:
            print(f"[ERROR] Voicefox gagal: {e}")
            audio_url = None
        
        # Mengirimkan balasan kembali ke HTML
        return {"balasan": balasan_ai, "audio": audio_url}
        
    except Exception as e:
        print(f"[ERROR] Koneksi ke LM Studio gagal: {e}")
        return {"balasan": "Maaf, sepertinya koneksiku ke otak LLM sedang terputus. Pastikan Local Server di LM Studio sudah menyala ya!"}

@app.post("/api/chat")
async def chat_dengan_waifu(pesan: PesanMasuk):
    # Rute untuk chat via Teks biasa
    return proses_chat_llm(pesan.chat)

@app.post("/api/voice-chat")
async def voice_chat_dengan_waifu(audio: UploadFile = File(...)):
    # Rute untuk chat via Suara (Microphone)
    print("\n[SISTEM] Menerima file audio dari frontend, sedang menganalisis...")
    
    # 1. Simpan audio sementara
    temp_audio_path = f"temp_{audio.filename}"
    with open(temp_audio_path, "wb") as buffer:
        buffer.write(await audio.read())
        
    # 2. Transcribe menggunakan Whisper
    try:
        print("[WHISPER] Mulai transkripsi...")
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
    