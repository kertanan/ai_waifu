# 🌸 AI Waifu Project — Sakura & Yiyi

> Proyek **AI Virtual Companion** berbasis LLM lokal dengan dua karakter interaktif:
> - **Yiyi** — Model 2.5D Live2D (PixiJS + Cubism 4)
> - **Sakura** — Model 3D VRM (Three.js + @pixiv/three-vrm)

---

## 📋 Daftar Isi

- [Tentang Proyek](#-tentang-proyek)
- [Arsitektur Sistem](#-arsitektur-sistem)
- [Alur Data (Data Flow)](#-alur-data-data-flow)
- [Struktur Folder](#-struktur-folder)
- [Prasyarat](#-prasyarat)
- [Instalasi](#-instalasi)
- [Konfigurasi Environment](#-konfigurasi-environment)
- [Menjalankan Proyek](#-menjalankan-proyek)
- [API Endpoint](#-api-endpoint)
- [Modul & Komponen](#-modul--komponen)
- [Sistem Karakter Ganda](#-sistem-karakter-ganda)
- [Tech Stack](#-tech-stack)
- [Troubleshooting](#-troubleshooting)

---

## 🎯 Tentang Proyek

AI Waifu Project adalah sistem interaktif yang menggabungkan:

- **LLM Lokal** via [LM Studio](https://lmstudio.ai/) untuk menghasilkan respons karakter
- **Speech-to-Text** via [OpenAI Whisper](https://github.com/openai/whisper) untuk voice chat
- **Text-to-Speech** via [VOICEVOX](https://voicevox.hiroshiba.jp/) untuk suara karakter Jepang
- **Live Lip-Sync** — audio dari VOICEVOX langsung dihubungkan ke animasi model Live2D
- **Dual Character System** — switch antara model 2.5D (Live2D) dan 3D (VRM) secara real-time
- **Translator** untuk terjemahan otomatis Indonesia → Jepang
- **FAISS Vector Store** untuk memori dan pencarian semantik

---

## 🏗 Arsitektur Sistem

```
┌──────────────────────────────────────────┐
│            FRONTEND (Browser)            │
│                                          │
│  ┌──────────┐        ┌────────────────┐  │
│  │ Live2D   │        │   3D VRM       │  │
│  │ Canvas   │◄──────►│   Canvas       │  │
│  │ (Yiyi)  │ switch │  (Sakura)      │  │
│  └──────────┘        └────────────────┘  │
│       │                                  │
│  ┌────▼───────────────────────────────┐  │
│  │      Chat UI (index.html)          │  │
│  │  [Text Input] [Mic Button] [Send]  │  │
│  └────────────────────────┬───────────┘  │
└───────────────────────────┼──────────────┘
                            │ HTTP (POST)
                            ▼
              ┌─────────────────────────────┐
              │   FastAPI Server            │
              │   api_server.py :8080       │
              │                             │
              │  /api/chat  ─────────────►  │
              │  /api/voice-chat ────────►  │──► Whisper STT
              └──────────────┬──────────────┘
                             │
              ┌──────────────┼───────────────┐
              ▼              ▼               ▼
       ┌────────────┐ ┌───────────┐  ┌──────────────┐
       │  LM Studio │ │ VOICEVOX  │  │  FAISS       │
       │  LLM :1234 │ │ TTS :50021│  │  Vector Store│
       └────────────┘ └─────┬─────┘  └──────────────┘
                            │
                     ┌──────▼──────┐
                     │ reply.wav   │
                     │ (audio out) │
                     └─────────────┘
```

### Arsitektur Alternatif (Go + Flask)

```
┌──────────┐   HTTP   ┌──────────┐   HTTP   ┌──────────┐
│  Go (Gin) │ ───────►│  Flask   │ ───────►│ LM Studio│
│  :8080    │ ◄───────│  :5000   │ ◄───────│  :1234   │
└──────────┘         └──────────┘         └──────────┘
```

---

## 🔄 Alur Data (Data Flow)

### Text Chat
```
User mengetik teks
    │
    ▼
sendMessage() [index.html]
    │  POST /api/chat  { chat: "...", number: 1 }
    ▼
api_server.py → proses_chat_llm()
    │  Baca source/system_prompt.txt
    │  POST ke LM Studio → dapat balasan
    │  Kirim teks ke VOICEVOX → simpan reply.wav
    ▼
Response JSON { balasan: "...", audio: "/audio/reply.wav" }
    │
    ▼
Frontend:
    ├── Tampilkan teks di bubble chat
    ├── Putar audio (new Audio())
    └── Lip-sync ke model Live2D (.speak())
```

### Voice Chat
```
User klik tombol 🎤
    │
    ▼
toggleRecording() → MediaRecorder (audio/webm)
    │  Klik ⏹️ → stop recording
    │  POST /api/voice-chat (FormData: audio file)
    ▼
api_server.py → whisper_model.transcribe()
    │  Hasil teks → proses_chat_llm()
    ▼
(alur sama seperti Text Chat di atas)
```

---

## 📁 Struktur Folder

```
AI-Waifu-Project/
├── api_server.py                    # 🚀 Entry point — FastAPI server utama
├── requirements.txt                 # 📦 Python dependencies
├── .env                             # 🔐 Environment variables (JANGAN di-commit!)
├── .env.example                     # 📝 Template environment variables
├── go.mod / go.sum                  # 🐹 Go module (backend alternatif Gin)
├── package.json                     # 📦 Node.js (PixiJS CDN — referensi saja)
│
├── frontend/                        # 🎨 Web Frontend
│   ├── index.html                   #    └─ Halaman utama (UI + Live2D + chat logic)
│   ├── style.css                    #    └─ Stylesheet dasar
│   ├── app.js                       #    └─ Three.js + VRM loader (3D Sakura)
│   └── asset/                       #    └─ Aset gambar/media lokal
│
├── call_another_character/          # 🔄 Loader karakter 3D alternatif
│   └── another_character.js         #    └─ Three.js VRM loader (sama dgn app.js)
│
├── Backend/                         # 🖥 Backend terstruktur
│   ├── API/                         #    └─ Konfigurasi API model
│   ├── app.py                       #    └─ Entry point Flask
│   ├── config.py                    #    └─ Konfigurasi koneksi LM Studio
│   ├── model/                       #    └─ Data model (character_profile.json)
│   ├── route/                       #    └─ Route handler (chat.py)
│   ├── service/                     #    └─ Business logic
│   │   ├── llm_service.py           #       ├─ LLM integration
│   │   ├── emotion_service.py       #       ├─ Emotion detection
│   │   └── memory_service.py        #       └─ Conversation memory
│   └── utilis/                      #    └─ Utilities (text processing)
│
├── LLM/                             # 🧠 Modul Language Model
│   ├── brain.py                     #    └─ Flask server untuk proses LLM
│   ├── intent_classifier.py         #    └─ Klasifikasi intent user
│   ├── response_filter.py           #    └─ Filter respons AI
│   └── sentiment_analysis.py        #    └─ Analisis sentimen
│
├── translator/                      # 🌐 Modul Terjemahan
│   └── translate.py                 #    └─ ID → JA translation (deep-translator)
│
├── speech/                          # 🔊 Modul Text-to-Speech
│   ├── voicefox.py                  #    └─ VOICEVOX TTS client + text preprocessor
│   ├── TTS/                         #    └─ TTS model resources
│   └── utils/                       #    └─ Audio utilities
│
├── data/                            # 💾 Data & Vector Store
│   ├── Faiss_Vector.py              #    └─ FAISS vector search engine
│   ├── dataset.json                 #    └─ Dataset karakter
│   └── conversation_logs/           #    └─ Log percakapan
│
├── Artificial_Intelligencce(traning)/ # 🎭 Integrasi VTube Studio
│   └── Character.py                 #    └─ Koneksi VTube Studio via pyvts
│
├── source/                          # 📚 Sumber pengetahuan (system_prompt.txt, dll.)
├── Character/                       # 🖼 Aset karakter
│   ├── PinkHair_workshop_*/         #    └─ Model Live2D Yiyi (.model3.json)
│   └── OG/sakura.vrm                #    └─ Model 3D VRM Sakura
├── Assets/                          # 🖼 Aset umum (background, thumbnail)
│   └── thumbnail/                   #    └─ Thumbnail sidebar (Yiyi & Sakura)
├── voicefox_source/reply.wav        # 🎵 Audio output TTS (overwrite setiap respons)
├── 3d model/                        # 🧊 Model 3D raw (base model & animations)
└── .venv/                           # 🐍 Python virtual environment
```

---

## ⚙ Prasyarat

| Software | Versi Minimum | Kegunaan |
|---|---|---|
| **Python** | 3.10+ | Runtime utama |
| **LM Studio** | Terbaru | LLM lokal (port 1234) |
| **VOICEVOX** | Terbaru | TTS engine Jepang (port 50021) |
| **VTube Studio** | Terbaru | Live2D character control (opsional) |
| **Go** | 1.26+ | Backend alternatif Gin (opsional) |
| **Node.js** | 18+ | Frontend PixiJS (opsional, sudah via CDN) |

> **GPU Note:** Whisper berjalan di CPU secara default (`fp16=False`). Ganti model `"base"` ke `"turbo"` di `api_server.py` jika GPU-mu cukup kuat.

---

## 🚀 Instalasi

### 1. Clone Repository

```bash
git clone https://github.com/kertanan/AI-model-training-project.git
cd AI-model-training-project
```

### 2. Setup Python Virtual Environment

```bash
# Buat virtual environment
python -m venv .venv

# Aktifkan (Windows PowerShell):
.\.venv\Scripts\Activate.ps1

# Aktifkan (Windows CMD):
.\.venv\Scripts\activate.bat

# Aktifkan (Linux/macOS):
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables

```bash
# Salin template
copy .env.example .env

# Edit .env dan isi nilai yang sesuai
```

---

## 🔐 Konfigurasi Environment

Edit file `.env` sesuai setup kamu:

| Variable | Default | Keterangan |
|---|---|---|
| `LM_STUDIO_URL` | `http://127.0.0.1:1234/v1/chat/completions` | URL endpoint LM Studio |
| `LM_STUDIO_MODEL` | `ibm/granite-4-micro` | Model LLM yang digunakan |
| `LM_API_TOKEN` | — | API token (dari LM Studio) |
| `API_HOST` | `127.0.0.1` | Host FastAPI server |
| `API_PORT` | `8080` | Port FastAPI server |
| `FLASK_PORT` | `5000` | Port Flask brain server |
| `VOICEVOX_URL` | `http://127.0.0.1:50021` | URL VOICEVOX engine |
| `VOICEVOX_SPEAKER_ID` | `8` | ID suara karakter |
| `EMBEDDING_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Model embedding untuk FAISS |

---

## ▶ Menjalankan Proyek

### Mode Cepat (FastAPI saja)

```bash
# 1. Pastikan LM Studio terbuka & Local Server aktif (port 1234)
# 2. Pastikan VOICEVOX terbuka & berjalan (port 50021)
# 3. Aktifkan venv, lalu:
python api_server.py
```

Buka browser → `http://localhost:8080`

### Mode Lengkap (Semua Layanan)

```bash
# Terminal 1: LM Studio → jalankan via GUI, aktifkan Local Server

# Terminal 2: FastAPI Server (server utama)
python api_server.py

# Terminal 3: Flask Brain (opsional, untuk arsitektur Go)
python LLM/brain.py

# Terminal 4: VOICEVOX → jalankan via GUI (port 50021)
```

---

## 📡 API Endpoint

### `POST /api/chat`

Mengirim pesan teks ke AI dan menerima balasan + audio.

**Request Body:**
```json
{
    "chat": "Halo Sakura, apa kabar?",
    "number": 1
}
```

**Response:**
```json
{
    "balasan": "*tersenyum tipis* Hah? Tuan tiba-tiba bertanya kabar? ...",
    "audio": "/audio/reply.wav"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"chat": "Halo!", "number": 1}'
```

---

### `POST /api/voice-chat`

Mengirim audio dari mikrofon, ditranskripsi Whisper, lalu diproses seperti text chat.

**Request:** `multipart/form-data` dengan field `audio` (file `.webm`)

**Response:** (sama dengan `/api/chat`)
```json
{
    "balasan": "...",
    "audio": "/audio/reply.wav"
}
```

---

### Static Routes

| Path | Sumber | Keterangan |
|---|---|---|
| `GET /` | `frontend/` | Halaman web utama |
| `GET /Assets/*` | `Assets/` | Background, thumbnail |
| `GET /audio/*` | `voicefox_source/` | File audio reply.wav |
| `GET /Character/*` | `Character/` | Aset model Live2D & VRM |

---

## 🧩 Modul & Komponen

### `api_server.py` — Server Utama (FastAPI)

| Fungsi/Route | Deskripsi |
|---|---|
| `proses_chat_llm(teks)` | Orchestrator: kirim ke LM Studio → dapat balasan → kirim ke VOICEVOX |
| `POST /api/chat` | Terima teks, panggil `proses_chat_llm` |
| `POST /api/voice-chat` | Terima audio webm → Whisper transcribe → `proses_chat_llm` |
| Static mounts | Sajikan frontend, Assets, audio, Character |

**Dependencies kunci:** `whisper`, `requests`, `fastapi`, `uvicorn`, `python-multipart`

---

### `speech/voicefox.py` — TTS Client (VOICEVOX)

| Fungsi | Deskripsi |
|---|---|
| `preprocess_text(text)` | Bersihkan tag ekspresi `(senyum)`, tweak tanda baca Jepang untuk intonasi natural |
| `generate_play_audio(text, ...)` | Query ke VOICEVOX `/audio_query` → `/synthesis` → simpan `voicefox_source/reply.wav` |

**Parameter TTS:**
```python
generate_play_audio(
    text,
    speaker_jp=14,   # ID karakter suara (14 = Meiメイ冥鳴ひまり)
    speed=1.0,       # Kecepatan bicara
    pitch=0.0,       # Nada suara
    intonation=1.0,  # Intonasi (1.0 = natural)
    volume=1.0
)
```

---

### `frontend/index.html` — UI Utama

| Komponen | Deskripsi |
|---|---|
| `#container-2d` / `#live2d-canvas` | Kanvas PixiJS untuk model Live2D Yiyi |
| `#container-3d` / `#three-canvas` | Kanvas Three.js untuk model VRM Sakura |
| Sidebar thumbnail | Klik gambar untuk switch karakter (memanggil `window.switchCharacter`) |
| `#chat-box` | Area tampilan pesan (bubble chat) |
| `#user-input` | Input teks + Enter key support |
| `#mic-btn` | Toggle microphone recording (🎤 / ⏹️) |
| `window.switchCharacter(type)` | Fungsi global untuk switch antara `'2d'` dan `'3d'` |

**Live2D Libraries (CDN):**
```html
<script src="https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/pixi.js@6.5.2/..."></script>
<script src="https://cdn.jsdelivr.net/npm/pixi-live2d-display/dist/cubism4.min.js"></script>
```

---

### `frontend/app.js` — 3D VRM Renderer (Three.js)

| Komponen | Deskripsi |
|---|---|
| `THREE.WebGLRenderer` | Renderer WebGL transparan (alpha: true) |
| `GLTFLoader + VRMLoaderPlugin` | Load file `.vrm` dari `/Character/OG/sakura.vrm` |
| `OrbitControls` | Kontrol kamera (rotate, zoom) |
| `animate()` | Game loop — update VRM + render scene |
| `window.waifuModel3D` | Referensi global ke objek VRM |

**Camera default:**
```javascript
camera.position.set(0, 1.4, 4.0);   // Mundur jauh agar seluruh badan terlihat
controls.target.set(0, 1.3, 0);     // Fokus ke area dada/kepala
```

---

### `data/Faiss_Vector.py` — Vector Store

Mengindeks file `.txt` dari folder `source/` menggunakan HuggingFace embeddings multilingual dan FAISS sebagai database vektor untuk pencarian semantik.

```python
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
db = FAISS.from_documents(docs, embeddings)
results = db.similarity_search("apa itu waifu?")
```

---

## 🎭 Sistem Karakter Ganda

Proyek ini mendukung dua karakter yang dapat di-switch secara real-time melalui sidebar thumbnail:

| | Yiyi | Sakura |
|---|---|---|
| **Dimensi** | 2.5D (Live2D) | 3D (VRM) |
| **Model** | `Character/PinkHair_workshop_*/yiyi_chair.model3.json` | `Character/OG/sakura.vrm` |
| **Renderer** | PixiJS + Cubism 4 | Three.js + @pixiv/three-vrm |
| **Scale** | `0.08` (terhadap lebar layar) | Kamera FOV 35°, jarak 4.0 |
| **Lip-sync** | ✅ via `.speak(audioUrl)` | ❌ (belum diimplementasi) |
| **Thumbnail** | `Assets/thumbnail/Thumbnail_yiyi.png` | `Assets/thumbnail/Thumbnail_sakura.png` |

**Cara kerja switch:**
```javascript
window.switchCharacter('2d');  // Tampilkan Yiyi, sembunyikan Sakura
window.switchCharacter('3d');  // Tampilkan Sakura, sembunyikan Yiyi
```
Border thumbnail berwarna `#ff6b81` menandai karakter aktif.

---

## 🛠 Tech Stack

| Layer | Teknologi |
|---|---|
| **Frontend — 2.5D** | HTML, CSS, PixiJS v6, Cubism 4 SDK, pixi-live2d-display |
| **Frontend — 3D** | Three.js r154, @pixiv/three-vrm v2, GLTFLoader, OrbitControls |
| **API Server** | FastAPI, Uvicorn, python-multipart |
| **Speech-to-Text** | OpenAI Whisper (model: base) |
| **LLM Engine** | LM Studio (OpenAI-compatible API, model: ibm/granite-4-micro) |
| **TTS** | VOICEVOX (speaker 14: 冥鳴ひまり) |
| **Translation** | deep-translator (Google Translate ID → JA) |
| **Vector DB** | FAISS + LangChain + sentence-transformers |
| **Alt Backend** | Flask, Go (Gin) |
| **Live2D Control** | VTube Studio + pyvts |

---

## 🐛 Troubleshooting

### "Koneksi ke LM Studio gagal"
- Buka LM Studio → tab **Local Server** → klik **Start Server**
- Pastikan model sudah di-load (loaded, bukan hanya downloaded)
- Default port: `1234`

### "VOICEVOX error"
- Buka aplikasi VOICEVOX, pastikan berjalan di port `50021`
- Cek speaker ID yang valid (lihat daftar di UI VOICEVOX)

### "Whisper gagal / voice chat tidak bekerja"
- Pastikan `openai-whisper` sudah ter-install: `pip install openai-whisper`
- Pastikan `python-multipart` ter-install (wajib untuk `UploadFile`): `pip install python-multipart`
- Whisper pertama kali akan mengunduh model `base` (~150MB) secara otomatis

### "Model Live2D/VRM tidak muncul"
- Pastikan path model benar: `Character/PinkHair_workshop_*/yiyi_chair.model3.json`
- Pastikan file VRM ada di: `Character/OG/sakura.vrm`
- Cek Console browser (F12) untuk error detail

### "Module not found"
- Pastikan virtual environment aktif: `.venv\Scripts\Activate.ps1`
- Jalankan ulang: `pip install -r requirements.txt`

### "Port sudah digunakan"
```bash
netstat -ano | findstr :8080
```
Ubah port di `.env` → `API_PORT=8081` (lalu restart server)

### "Lip-sync tidak berjalan"
- Lip-sync hanya berfungsi untuk model 2.5D (Yiyi)
- Model harus mendukung method `.speak()` dari pixi-live2d-display
- Jika error: `console.warn` di browser — model tidak support, diabaikan secara graceful

---

## 📝 Changelog

### v2.0 (2026-06)
- ✅ Ditambah sistem karakter ganda: Live2D Yiyi + 3D VRM Sakura
- ✅ Sidebar thumbnail untuk switch karakter
- ✅ Voice chat via Whisper STT (`/api/voice-chat`)
- ✅ Live lip-sync ke model Live2D setelah respons audio
- ✅ Text preprocessing di VOICEVOX (hapus tag ekspresi, tweak intonasi)

### v1.0 (2026-05)
- ✅ FastAPI server dengan `/api/chat`
- ✅ Integrasi LM Studio (OpenAI-compatible)
- ✅ VOICEVOX TTS
- ✅ FAISS vector store untuk memori semantik
- ✅ Translator Indonesia → Jepang

---

<p align="center">
  <i>Built with 💖 by Ferdy — "Bukan berarti aku membuatnya untukmu ya, Tuan!"</i>
</p>#   a i _ w a i f u  
 