# Waifu AI Assistant - System Workflow

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
        │ database.db   │ │  (Granite)    │ │  memory table │
        │               │ │  port 1234    │ │               │
        └───────────────┘ └───────────────┘ └───────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │         Voicevox TTS           │
                    │      (port 50021)              │
                    │  - Audio synthesis             │
                    │  - Generates reply.wav         │
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
| `/api/chat` | POST | `{chat: string, number: int}` | `{balasan: string, audio: string}` | Text chat |
| `/api/voice-chat` | POST | `FormData(audio: File)` | `{balasan: string, audio: string}` | Voice chat |

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
│ (Financial) │       │  (Granite)  │
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
- **Model:** IBM Granite (via LM Studio)
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
- Output: `voicefox_source/reply.wav`
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
6. Granite generates: "Halo! Aku baik-baik saja, kamu bagaimana?"
7. Response logged to database
8. Voicefox generates audio (Japanese)
9. Returns {balasan: "...", audio: "/audio/reply.wav"}
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
   - LM Studio running on port 1234 with Granite model
   - Voicevox running on port 50021

3. **Database**
   - SQLite database auto-created on first run

### Starting the System

```bash
# Start API Server
python api_server.py

# Access at http://localhost:8080
```

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
