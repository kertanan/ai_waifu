# Arsitektur Deployment Sakura

Rencana menjalankan Sakura (waifu AI) agar bisa diakses dari perangkat lain, dengan biaya serendah mungkin karena ini proyek individu. Dokumen ini dibagi per tahap. Mulai dari Tahap 1, lalu naik tahap hanya kalau memang butuh.

## Kondisi sekarang

| Komponen | Lokasi | Port |
|---|---|---|
| `api_server.py` (FastAPI): frontend, `/api/chat`, `/api/voice-chat`, aset, audio | Laptop | `127.0.0.1:8080` |
| LM Studio: LLM `qwen/qwen3-4b-2507` (fine-tune `sakura-qwen3-4b` sedang dikembangkan) | Laptop | `127.0.0.1:1234` |
| GPT-SoVITS (suara char001) | Laptop | `127.0.0.1:9880` |
| VOICEVOX (fallback TTS) | Laptop | `127.0.0.1:50021` |
| Whisper (speech-to-text, CPU) | Di dalam proses `api_server.py` | — |
| `database.db`, FAISS (memori) | Laptop | — |

Frontend memanggil API dengan path relatif (`/api/chat`, `/api/voice-chat`) dan semuanya disajikan dari satu port. Jadi **cukup port 8080 yang dibuka lewat tunnel**. Port lain tetap tertutup di localhost.

Laptop: RTX 2050 4 GB VRAM (sekitar 3,3 GB terpakai GPT-SoVITS), RAM 16 GB.

---

## Tahap 1: Gratis, laptop sebagai server (dikerjakan sekarang)

```
 HP / perangkat lain                         Laptop (semua berjalan di 127.0.0.1)
┌──────────────┐   HTTPS (Tailscale)     ┌───────────────────────────────────────────┐
│ Browser      │ ──────────────────────▶ │ api_server.py :8080  ← satu-satunya pintu │
│ (chat, mic,  │                         │   ├─ frontend + avatar 3D (statis)        │
│  avatar 3D)  │                         │   ├─ /api/chat, /api/voice-chat (Whisper) │
└──────────────┘                         │   ├─ /api/event  ◀── agent lokal          │
                                         │   └─ WebSocket (push reaksi Sakura)       │
 (opsional) Cloudflare Tunnel            │                                           │
 + Cloudflare Access (login) ──────────▶ │ LM Studio :1234   ┐                       │
                                         │ GPT-SoVITS :9880  ├─ JANGAN dibuka keluar │
                                         │ VOICEVOX :50021   ┘                       │
                                         │ database.db, FAISS                        │
                                         │                                           │
                                         │ Agent: hook PowerShell, ekstensi VS Code, │
                                         │        scan aktivitas → POST /api/event   │
                                         └───────────────────────────────────────────┘
```

| Taruh di | Isi | Catatan |
|---|---|---|
| **Tailscale** (utama) | `tailscale serve` → `127.0.0.1:8080` | Hanya perangkat Anda yang bisa akses. HTTPS otomatis, sehingga mikrofon di browser HP jalan. Paket personal gratis. |
| **Cloudflare Tunnel** (opsional) | `cloudflared` → `127.0.0.1:8080` saja | Untuk akses dari perangkat tanpa Tailscale, atau untuk dibagikan. **Wajib dilindungi Cloudflare Access** (login email). Alamat tetap butuh domain di Cloudflare. Untuk tes sementara bisa pakai quick tunnel `*.trycloudflare.com`. |
| **Tetap lokal** | LLM, TTS, VOICEVOX, database, agent | Agent mengirim event langsung ke `127.0.0.1:8080`, tidak lewat tunnel. |

Perubahan kode: hampir tidak ada. `uvicorn` tetap mendengarkan di `127.0.0.1:8080`, dan tunnel yang meneruskan ke sana.

Kekurangan: Sakura hanya bisa diakses saat laptop menyala.

---

## Tahap 2: Selalu online, masih gratis (kalau sudah butuh)

```
 Browser ──HTTPS──▶ Cloudflare Pages ──────── frontend + model 3D (VRM) via CDN
    │
    └──WebSocket/API──▶ Cloudflare Tunnel + Access ──▶ Oracle Always Free VM ("gateway")
                                                       ├─ api_server: auth, WebSocket hub, router
                                                       ├─ database memori, FAISS
                                                       ├─ router coding ──▶ API LLM (tier gratis)
                                                       └─ Tailscale ──▶ Laptop ("GPU worker")
                                                                        ├─ LM Studio (Sakura)
                                                                        ├─ GPT-SoVITS
                                                                        └─ agent → gateway /api/event
```

| Taruh di | Isi |
|---|---|
| **Cloudflare Pages** | Semua aset statis: HTML/JS/CSS, model 3D, animasi |
| **Oracle Always Free VM** (gateway, tanpa GPU) | Login, WebSocket hub, memori/database, router chat ↔ coding, pemanggilan API coding |
| **Laptop** (GPU worker) | LLM Sakura + GPT-SoVITS, hanya bisa diakses gateway lewat Tailscale (ACL: gateway saja) |
| **API LLM eksternal** | Model coding (tier gratis, misalnya Gemini / Groq / OpenRouter) |

Kalau laptop mati, gateway memakai cadangan: LLM lewat API dan jawaban sebatas teks tanpa suara.

Yang perlu diubah di kode:
- `api_server.py` dipecah: gateway (ringan) dan worker (LLM/TTS).
- Worker mendengarkan di IP Tailscale, bukan di `127.0.0.1`, dan diproteksi ACL.
- URL LLM/TTS di `.env` gateway diarahkan ke IP Tailscale laptop.

---

## Tahap 3: Punya GPU server (nanti)

Server GPU menggantikan posisi laptop sebagai worker di jaringan Tailscale yang sama. Gateway dan frontend tidak berubah.

Rekomendasi hardware:

| Bagian | Minimal | Disarankan | Ideal |
|---|---|---|---|
| GPU (VRAM) | 12 GB (RTX 3060 12GB) | 16 GB (RTX 4060 Ti / 5060 Ti 16GB) | **24 GB** (RTX 3090 bekas / 4090, L4 / A10 di cloud) |
| RAM | 16 GB | **32 GB** | 64 GB (training/merge 7–8B) |
| Storage | NVMe 500 GB | NVMe 1 TB | NVMe 1 TB+ |
| CPU | 6 core | 6–8 core | 8 core |

Perkiraan VRAM per komponen: Sakura 4B Q4 ±3–4 GB, GPT-SoVITS ±3,3 GB, Whisper ±1–4 GB, model coding 7–8B ±5–7 GB, model vision kecil ±3–6 GB, training QLoRA 4B ±6–8 GB.

Opsi hemat: sewa GPU per jam (Vast.ai / RunPod) hanya saat training, lalu matikan.

---

## Alur event: Sakura menyemangati saat ada error

```
[Sumber event]                         [api_server]                         [Output]
Hook PowerShell / VS Code /   ──POST──▶  /api/event                    ──▶  teks (frontend)
wrapper `sakura run` / scan              ├─ cooldown + filter               suara (GPT-SoVITS)
  {type: "runtime_error",                ├─ reaksi bertingkat               ekspresi avatar 3D
   lang: "python",                        └─ LLM Sakura → 1 kalimat
   error: "KeyError"}                              │
                                         WebSocket push ke frontend
```

- **Error pertama:** semangat singkat, misalnya 「べ、別に心配してないけど…頑張りなさいよね！」
- **Error berulang:** lebih perhatian, misalnya menyarankan istirahat.
- **Berhasil setelah error:** ikut senang, misalnya 「ふん、やればできるじゃない。…ちょっとだけ見直したわ。」
- Payload event hanya berisi jenis error dan bahasanya, **tanpa isi kode atau path lengkap**.
- Kode tidak dibacakan oleh TTS. Detail error ditampilkan sebagai teks.

---

## Checklist keamanan (sebelum dibuka keluar)

- [ ] Ada login: Tailscale (otomatis) atau Cloudflare Access. `api_server.py` saat ini belum punya autentikasi.
- [ ] Persempit CORS: sekarang `allow_origins=["*"]` + `allow_credentials=True`. Ganti ke domain sendiri.
- [ ] Port `1234`, `9880`, `50021` tidak pernah diteruskan ke tunnel.
- [ ] `.env` dan token API tidak ter-commit dan tidak dikirim ke frontend.
- [ ] Event dari agent tidak memuat potongan kode atau path lengkap.
- [ ] Jangan kirim kode rahasia ke API LLM tier gratis (datanya bisa dipakai untuk training oleh penyedia).

---

## Urutan pengerjaan

1. **Tahap 1:** pasang Tailscale → `tailscale serve` ke port 8080 → tes dari HP (Rp0).
2. `/api/event` + WebSocket + hook PowerShell (fitur penyemangat saat error).
3. Router coding ke API LLM gratis.
4. Avatar 3D (VRM) menerima perintah ekspresi lewat WebSocket.
5. **Tahap 2** kalau butuh selalu online, **Tahap 3** kalau proyek makin serius.

> Ketentuan tier gratis (Tailscale, Cloudflare, Oracle, Kaggle/Colab, API LLM) dan harga hardware bisa berubah. Cek halaman resmi sebelum memakai.
