# Waifu AI Assistant - System Workflow

## Recap terakhir (2026-11-20): baca ini dulu sebelum lanjut

Bagian ini merangkum kondisi proyek dan pekerjaan yang belum selesai. Daftar lengkap ada di [TODO.md](TODO.md), rencana server di [DEPLOYMENT_ARCHITECTURE.md](DEPLOYMENT_ARCHITECTURE.md).

### Kondisi sekarang

- **LLM:** `.env` memakai `LM_STUDIO_MODEL=qwen/qwen3-4b-2507` (model dasar) dengan system prompt bahasa Jepang di `source/system_prompt.txt`. Prompt lama (bahasa Inggris) disimpan di `source/system_prompt_original_en.txt`.
- **Fine-tune v1** (`sakura-qwen3-4b` di LM Studio) kalah dari model dasar + prompt Jepang:
  - Model dasar: Jepang 20/20, tsundere 15/20, fakta 6/6.
  - v1: Jepang 16/20, tsundere 8/20, fakta 3/6, dan kadang balasan kosong atau berawalan tag `<tool_call>`.
  - Penyebabnya: data latih berisi blok `<think></think>` kosong, dan sampelnya cuma ±2.7k.
  - File: GGUF di `E:\lm_studio\model\local\sakura-qwen3-4b-GGUF\`, LoRA di `data/result_of_finetuning/sakura_lora`.
- **Fine-tune dihentikan (2026-11-20):** GPU T4 di Colab/Kaggle tidak kuat untuk Qwen3-4B. Notebook v2 (`tools/finetune/sft_qlora_sakura_colab.ipynb`) disimpan tapi tidak dijalankan. Sakura tetap memakai model dasar + prompt Jepang.
- **Server (`api_server.py`)** sudah diperbaiki untuk chat paralel:
  - Rute `/api/chat` dan `/api/voice-chat` berupa `def` biasa, jadi jalan di threadpool.
  - Teks dikirim duluan. Audio dibuat di antrean TTS latar belakang, lalu frontend mengambilnya lewat `GET /api/audio/{id}`.
  - Balasan kosong dicoba ulang (`LLM_MAX_ATTEMPTS`, default 3). Kalau tetap kosong, dipakai kalimat cadangan.
  - Database dikunci dengan `db_lock`. `clean_reply` di `LLM/llm_config.py` membuang tag `<tool_call>`/`<think>`.
- **TTS:** GPT-SoVITS tetap utama, VOICEVOX jadi cadangan. Kalau SoVITS mati, `speech/voicefox.py` melewatinya selama 60 detik (`SOVITS_RETRY_SEC`). Audio disimpan di `voicefox_source/replies/<uuid>.wav` dan dihapus otomatis setelah 1 jam.
- **Hasil tes 2026-11-18** (`sakura-qwen3-4b` + VOICEVOX, SoVITS mati): 1 chat → teks 4,7 dtk. 2 chat paralel → teks 5,5 dtk dan 6,0 dtk. Chat teks, voice chat (Whisper) dan upload file berbahaya semuanya OK.

### Catatan penting

- Jalankan server dengan Python utama: `D:\python\python api_server.py`. Venv `E:\mitm-env` yang aktif di terminal berisi paket `whisper` yang salah.
- Laptop (RTX 2050 4 GB, RAM 16 GB) memproses LM Studio dan VOICEVOX satu per satu, jadi chat ke-3 yang dikirim bersamaan tetap menunggu. Ini batas hardware, bukan bug.
- CLI LM Studio: `~/.lmstudio/bin/lms`. Folder model: `E:\lm_studio\model`.
- Saat tes, jangan nyalakan GPT-SoVITS kecuali memang diminta.
- **GitHub (`kertanan/ai_waifu`, publik):** sejak 2026-11-20 `.env`, `token.txt`, `database.db`, `data/`, `Assets/book_train/` dan file `.wav` masuk `.gitignore`. Ketiga file rahasia masih ada di riwayat commit pertama, jadi token/kunci di dalamnya harus diganti.
- **Online (2026-11-20):** frontend di https://ai-waifu.ferdisaputra2833.workers.dev (Cloudflare Workers, `wrangler.jsonc` + `tools/build_pages.sh`, env `SKIP_DEPENDENCY_INSTALL=1` dan `SAKURA_API_URL`). Backend tetap di laptop lewat quick tunnel `cloudflared tunnel --url http://127.0.0.1:8080`; setiap alamat tunnel berubah, perbarui `SAKURA_API_URL` lalu deploy ulang. Domain workers.dev sudah masuk `ALLOWED_ORIGINS` di `.env`. Belum ada login (perlu Cloudflare Access).
- Frontend memakai `API_URL` (dari `window.SAKURA_API_URL`, default kosong = server yang sama). Isi kalau frontend di-host terpisah, misalnya di Cloudflare Pages.

### Belum dikerjakan (urutan yang disarankan)

1. **Tes end-to-end dengan GPT-SoVITS menyala.**
2. **Tahap 1, akses dari HP (gratis):** Tailscale + `tailscale serve` ke `127.0.0.1:8080`. Pastikan port 1234 / 9880 / 50021 tidak ikut terbuka.
3. **Fitur "Sakura menyemangati saat error":** `POST /api/event`, WebSocket `/ws`, dan hook PowerShell (contoh reaksi: 頑張れあなた).
4. **Router coding:** permintaan coding dikirim ke model coding. Sakura hanya membacakan ringkasan.
5. **Avatar 3D:** ekspresi dipicu WebSocket, lip-sync dari audio.
6. **Rapikan kode:**
   - Pipeline memori setelah `uvicorn.run(...)` di `api_server.py` tidak pernah jalan. Sambungkan ke chat atau hapus.
   - Batasi mount `/Assets`, karena sekarang ikut membuka `Assets/book_train` (187 MB).
   - Tinjau `/api/chat_db` (data keuangan).
7. **Atribusi dataset** CC-BY-4.0 (`scryptiam/anime-waifu-personality-chat`): hanya kalau model v1 atau dataset-nya dibagikan.

---

## System Overview

This is an AI Waifu chatbot system with Live2D/3D character visualization, voice interaction, memory management, and financial tracking capabilities.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                       │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │  Live2D Canvas   │  │  3D VRM Canvas   │  │     Chat Interface       │  │
│  │  (Yiyi Model)    │  │  (Sakura Model)  │  │  - Text Input            │  │
│  │                  │  │                  │  │  - Voice Recording        │  │
│  │  pixi.js +       │  │  Three.js +      │  │  - Message Display       │  │
│  │  live2d-display  │  │  three-vrm       │  │                          │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FASTAPI SERVER (port 8080)                         │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                           api_server.py                              │  │
│  │  - POST /api/chat          (Text chat)                              │  │
│  │  - POST /api/voice-chat    (Voice chat with Whisper STT)            │  │
│  │  - Static file serving     (Assets, Audio, Characters, Frontend)    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
        ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
        │   DB Module   │ │  LLM Module   │ │  Memory Mgr   │
        │ db_connect.py │ │   brain.py    │ │ memeory_      │
        │               │ │               │ │ Manage.py     │
        └───────────────┘ └───────────────┘ └───────────────┘
                │               │               │
                ▼               ▼               ▼
        ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
        │  SQLite DB    │ │  LM Studio    │ │  SQLite DB    │
        │ database.db   │ │ (Qwen3-4B)    │ │  memory table │
        │               │ │  port 1234    │ │               │
        └───────────────┘ └───────────────┘ └───────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │         Voicevox TTS           │
                    │      (port 50021)              │
                    │  - Audio synthesis             │
                    │  - replies/<uuid>.wav         │
                    └───────────────────────────────┘
```

---

## Component Details

### 1. Frontend Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Live2D Model | pixi.js + pixi-live2d-display | 2D character rendering (Yiyi) |
| 3D Model | Three.js + @pixiv/three-vrm | 3D character rendering (Sakura) |
| Chat UI | Vanilla JS | User interaction interface |
| Voice Recording | MediaRecorder API | Audio capture for STT |

**Character Switching:**
- Click thumbnail to switch between 2D (Yiyi) and 3D (Sakura)
- Visual indicator shows active character

---

### 2. Backend API Server (`api_server.py`)

**Main Endpoints:**

| Endpoint | Method | Input | Output | Description |
|----------|--------|-------|--------|-------------|
| `/api/chat` | POST | `{chat: string, number: int}` | `{balasan, audio_id, audio_wait}` | Text chat (teks langsung, audio menyusul) |
| `/api/voice-chat` | POST | `FormData(audio: File)` | `{balasan, audio_id, audio_wait}` | Voice chat (Whisper STT) |
| `/api/audio/{audio_id}` | GET | — | `{ready, url}` | Tunggu audio balasan selesai dibuat (long-poll) |

**Processing Flow:**

```
User Input (Text/Voice)
        │
        ▼
┌─────────────────┐
│  Voice Input?   │
└────────┬────────┘
         │
    Yes  │  No
    ▼    │
┌───────────────┐    ┌─────────────────┐
│ Whisper STT   │    │  Direct Text    │
│ (base model)  │    │                 │
└───────┬───────┘    └────────┬────────┘
        │                     │
        └──────────┬──────────┘
                   ▼
        ┌─────────────────┐
        │ proses_chat_llm │
        └────────┬────────┘
                 │
    ┌────────────┴────────────┐
    ▼                         ▼
┌─────────────┐       ┌─────────────┐
│ DB Check    │       │  LLM Call   │
│ (Financial) │       │ (Qwen3-4B)  │
└──────┬──────┘       └──────┬──────┘
       │                     │
       ▼                     ▼
┌─────────────┐       ┌─────────────┐
│ Financial   │       │ Log to DB   │
│ Response    │       └──────┬──────┘
└──────┬──────┘              │
       │                     ▼
       │            ┌─────────────────┐
       │            │  Voicefox TTS   │
       │            │  (Generate WAV) │
       │            └────────┬────────┘
       │                     │
       └──────────┬──────────┘
                  ▼
        ┌─────────────────┐
        │  JSON Response  │
        │  {balasan, audio}│
        └─────────────────┘
```

---

### 3. Database Module (`db_connect.py`)

**Tables:**

| Table | Columns | Purpose |
|-------|---------|---------|
| `interaksi_utama` | id, pesan_user, intent, time | Main interaction log |
| `log_obrolan` | id, interaksi_id, respon_ai, time | Chat response log |
| `data_keuangan` | id, interaksi_id, kategori, jumlah, time, keterangan | Financial transactions |
| `memory` | id, category, key, value, importance | User memory cache |

**Intent Detection:**

| Intent | Keywords | Action |
|--------|----------|--------|
| `keuangan_keluar` | beli, bayar, jajan, pengeluaran | Record expense |
| `keuangan_masuk` | gajian, dapat uang, pemasukan, nabung | Record income |
| `cek_keuangan` | sisa uang, cek uang, total | Check balance |
| `ngobrol_biasa` | (default) | Normal chat |

---

### 4. LLM Integration (`brain.py`)

**Configuration:**
- **Model:** `qwen/qwen3-4b-2507` via LM Studio (`LM_STUDIO_MODEL` di `.env`)
- **Endpoint:** `http://localhost:1234/v1/chat/completions`
- **System Prompt:** Loaded from `source/system_prompt.txt`
- **Temperature:** 0.7
- **Max Tokens:** 150

**Response Format:** OpenAI-compatible JSON

---

### 5. Memory System

**Memory Manager (`memeory_Manage.py`):**
- Extracts structured memories from user text
- Uses LLM to parse user input into JSON format
- Stores: category, key, value, importance

**Memory Storage (`save_memory.py`):**
- Saves extracted memories to SQLite
- Supports deduplication via key uniqueness

---

### 6. Voice Processing

**Speech-to-Text (Whisper):**
- Model: `base` (fast CPU inference)
- Input: WebM audio from browser
- Output: Transcribed text

**Text-to-Speech (Voicevox):**
- Endpoint: `http://127.0.0.1:50021`
- Speaker ID: 14 (Meimei Himari)
- Output: `voicefox_source/replies/<uuid>.wav` (dihapus otomatis setelah 1 jam)
- Features: Natural intonation, speed/pitch control

---

## Data Flow Examples

### Example 1: Text Chat

```
1. User types: "Halo, apa kabar?"
2. Frontend sends POST /api/chat {chat: "Halo, apa kabar?", number: 1}
3. proses_chat_llm() called
4. proses_pesan_utama() checks intent → "ngobrol_biasa" → not handled
5. LM Studio called with system_prompt + user message
6. Qwen3 generates: "Halo! Aku baik-baik saja, kamu bagaimana?"
7. Response logged to database
8. Voicefox generates audio (Japanese)
9. Returns {balasan, audio_id, audio_wait} → frontend menunggu GET /api/audio/{id}
10. Frontend displays message and plays audio
```

### Example 2: Voice Chat

```
1. User clicks mic, speaks: "Aku habis beli kopi 25 ribu"
2. Browser records audio, sends POST /api/voice-chat
3. Whisper transcribes audio to text
4. proses_chat_llm() called with transcribed text
5. proses_pesan_utama() detects intent → "keuangan_keluar"
6. Financial data extracted: {jumlah: 25000, kategori: "umum"}
7. Saved to data_keuangan table
8. Response generated with remaining balance
9. Voicefox generates audio
10. Returns response with audio
```

---

## Setup & Deployment

### Prerequisites

1. **Python Environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **External Services**
   - LM Studio running on port 1234 (`qwen/qwen3-4b-2507`)
   - GPT-SoVITS api_v2 running on port 9880 (main TTS, voice `char001`)
   - Voicevox running on port 50021 (fallback TTS)

3. **Database**
   - SQLite database auto-created on first run

### Starting the System

Urutan start: **LM Studio → GPT-SoVITS → API Server**.

```bash
# 1. Start GPT-SoVITS server (window terpisah, biarkan tetap terbuka)
tools\start_sovits_api.bat

# 2. Start API Server
D:\python\python api_server.py   # jangan pakai venv E:\mitm-env

# Access at http://localhost:8080
```

### Menjalankan GPT-SoVITS

GPT-SoVITS adalah TTS utama (suara hasil training `char001`). Kalau server ini
tidak jalan, `speech/voicefox.py` otomatis fallback ke VOICEVOX.

1. **Program** — paket Windows GPT-SoVITS v2Pro di `E:\GPT-SoVITS-v2pro-20250604`
   (pakai `runtime\python.exe` bawaan, tidak perlu venv). Kalau folder dipindah,
   ubah `GPT_SOVITS_DIR` di `tools\start_sovits_api.bat`.

2. **Jalankan server** — double-click `tools\start_sovits_api.bat`, atau manual:
   ```bat
   cd /d E:\GPT-SoVITS-v2pro-20250604
   runtime\python.exe api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
   ```
   Tunggu sampai muncul `Uvicorn running on http://127.0.0.1:9880`.

3. **Konfigurasi `.env`**
   ```env
   TTS_ENGINE=sovits            # "voicevox" untuk pakai VOICEVOX saja
   SOVITS_URL=http://127.0.0.1:9880
   SOVITS_MODEL_DIR=voice_model/char001/output
   SOVITS_TEXT_LANG=ja
   ```

4. **Model** — `voice_model/char001/output/` berisi bobot GPT (`.ckpt`), SoVITS
   (`.pth`), `ref.wav` + `ref.txt`, dan `model_info.json`. Bobot dikirim otomatis
   ke server (`/set_gpt_weights`, `/set_sovits_weights`) saat TTS pertama kali
   dipanggil — tidak perlu load manual di WebUI.

5. **Tes**
   ```bash
   python speech/voicefox.py
   ```
   Log `[VOICEFOX] Model 'char001' dimuat ke GPT-SoVITS` = berhasil.
   Log `GPT-SoVITS gagal (...), beralih ke VOICEVOX` = server belum jalan / error.

**Catatan VRAM (RTX 2050 4 GB):** GPT-SoVITS memakai ~3.3 GB VRAM. Whisper
dijalankan di CPU dan GPU offload LM Studio dikecilkan supaya tidak out-of-memory.
Kalau suara terdengar robot/berbeda, cek dulu apakah server SoVITS hidup
(kemungkinan sedang fallback ke VOICEVOX).

### Required Files

| File | Purpose |
|------|---------|
| `source/system_prompt.txt` | AI personality definition |
| `Character/` | Live2D/VRM model files |
| `Assets/` | Background images, thumbnails |
| `voicefox_source/` | Generated audio output |

---

## Development Workflow

### Adding New Features

1. **Backend Changes**
   - Edit `api_server.py` for new endpoints
   - Edit `db_connect.py` for database operations
   - Add new modules in respective folders

2. **Frontend Changes**
   - Edit `frontend/index.html` for UI
   - Edit `frontend/app.js` for 3D model logic
   - Edit inline `<script>` in HTML for chat logic

3. **LLM Changes**
   - Modify prompts in `source/system_prompt.txt`
   - Adjust parameters in `brain.py` or `api_server.py`

### Testing

```bash
# Test database
python test_db.py
python cekdb.py

# Test voice
python speech/voicefox.py
```

---

## Configuration Files

### Environment Variables (`.env`)

```
# Add any API keys or configuration here
```

### System Prompt (`source/system_prompt.txt`)

Define AI personality, response style, and behavioral rules.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Whisper fails to load | Check if `openai-whisper` installed, try smaller model |
| LM Studio connection error | Ensure LM Studio running on port 1234 |
| Voicevox error | Start Voicevox app on port 50021 |
| Database locked | Close other Python processes using database.db |
| Model not displaying | Check Character folder paths, verify model files |

---

## File Structure Summary

```
E:\Pembuatan Waifu\
├── api_server.py          # Main FastAPI server
├── database.db           # SQLite database
├── requirements.txt      # Python dependencies
├── package.json         # Node.js dependencies (pixi.js)
│
├── frontend/            # Web UI
│   ├── index.html      # Main HTML with chat UI
│   ├── app.js          # 3D model rendering
│   └── style.css       # Styles
│
├── Backend/            # Flask-based modules
│   ├── app.py
│   ├── config.py
│   ├── API/
│   ├── service/
│   ├── model/
│   └── route/
│
├── LLM/                # Language Model modules
│   ├── brain.py        # Main LLM integration
│   ├── intent_classifier.py
│   ├── sentiment_analysis.py
│   └── response_filter.py
│
├── memory_manager/     # Memory system
│   ├── memeory_Manage.py
│   ├── save_memory.py
│   ├── memory_cache.py
│   └── cache.py
│
├── db_connect/         # Database module
│   ├── db_connect.py
│   └── shema.py
│
├── speech/             # Voice processing
│   └── voicefox.py    # TTS
│
├── speach_to_text/     # STT
│   └── speach_to_text.py
│
├── Character/          # Live2D/VRM models
├── Assets/            # Static assets
├── source/            # System prompts
├── data/              # Dataset & vectors
└── prompt/            # Prompt templates
```

---

## Version History

- v1.0: Initial release with text chat, voice chat, memory system, financial tracking
