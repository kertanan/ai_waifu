# TODO: Sakura

Daftar pekerjaan sesuai [DEPLOYMENT_ARCHITECTURE.md](DEPLOYMENT_ARCHITECTURE.md). Centang `[x]` kalau sudah selesai.

## 0. Perbaikan dasar sebelum server dibuka

- [x] Rute `/api/chat` & `/api/voice-chat` tidak lagi memblokir server (`async def` → `def`, jalan di threadpool)
- [x] Audio balasan unik per jawaban (`voicefox_source/replies/<uuid>.wav`, otomatis dihapus setelah 1 jam), bukan lagi satu `reply.wav` yang saling menimpa
- [x] Upload suara aman: nama file dari browser tidak dipakai sebagai path (cegah `../`)
- [x] Whisper & TTS dipanggil satu per satu (lock), dan ada timeout ke LM Studio
- [x] CORS dipersempit, dengan origin diatur lewat `.env` `ALLOWED_ORIGINS` (default: localhost:8080)
- [x] `audio` bernilai `null` kalau TTS gagal (dulu tetap mengirim URL ke file lama)
- [x] Tes end-to-end dengan `sakura-qwen3-4b` + VOICEVOX (2026-11-18): chat teks, 2 chat paralel, voice chat (Whisper), upload nama berbahaya, semuanya OK
- [ ] Tes end-to-end dengan GPT-SoVITS menyala (user akan tes sendiri lewat workers.dev)
- [x] Balasan kosong → retry otomatis (maks. `LLM_MAX_ATTEMPTS`=3), lalu kalimat cadangan
- [x] Teks balasan dikirim dulu, audio dibuat di latar belakang (`audio_wait` → `GET /api/audio/{id}`); frontend memutar audio bergantian
- [x] Database dikunci (`db_lock`): cursor SQLite bersama aman dipakai chat paralel
- [x] GPT-SoVITS mati → dilewati 60 dtk (`SOVITS_RETRY_SEC`), tidak lagi membuang ±2 dtk per balasan
- [ ] Batas hardware: LM Studio & VOICEVOX tetap memproses satu per satu di laptop 4 GB (chat ke-3 menunggu). Baru hilang dengan GPU lebih besar
- [ ] Percobaan LLM yang kosong bisa memakan sampai `max_tokens` (±20 dtk) sebelum retry. Fine-tune v2 dihentikan, jadi perlu cara lain (misalnya `max_tokens` lebih kecil atau timeout per percobaan)
- [ ] Jalankan server dengan Python utama (`D:\python\python api_server.py`). Venv `E:\mitm-env` yang aktif di terminal berisi paket `whisper` yang salah

## 1. Tahap 1: akses dari HP, gratis (Tailscale)

- [ ] Install Tailscale di laptop & HP, login dengan akun yang sama
- [ ] `tailscale serve` → `127.0.0.1:8080`, lalu buka alamat `https://<laptop>.<tailnet>.ts.net` dari HP
- [ ] Tes chat teks, voice chat (mikrofon HP), dan audio balasan dari HP
- [ ] Pastikan port `1234` / `9880` / `50021` tidak ikut terbuka
- [x] Frontend statis di Cloudflare Workers (https://ai-waifu.ferdisaputra2833.workers.dev), build `sh tools/build_pages.sh`, `SKIP_DEPENDENCY_INSTALL=1` (2026-11-20)
- [x] Quick tunnel `cloudflared` → `127.0.0.1:8080`, alamatnya diisi ke `SAKURA_API_URL`; chat lewat tunnel OK (±10 dtk)
- [ ] Named tunnel + domain sendiri (alamat quick tunnel berganti tiap restart)
- [ ] Cloudflare Access di depan tunnel (sekarang backend terbuka untuk siapa saja yang tahu alamatnya)

## 2. Fitur "Sakura menyemangati saat error"

- [ ] Endpoint `POST /api/event` (`{type, lang, error}`, tanpa isi kode/path)
- [ ] Cooldown + reaksi bertingkat: error pertama → semangat, berulang → perhatian, berhasil setelah error → ikut senang
- [ ] Kumpulan kalimat siap pakai + variasi dari LLM
- [ ] WebSocket `/ws` supaya Sakura bisa bicara tanpa diajak chat (teks + URL audio + ekspresi)
- [ ] Frontend: terima pesan WebSocket → tampilkan teks, putar audio, ubah ekspresi
- [ ] Sumber event #1: hook PowerShell (`prompt` cek `$?` / `$LASTEXITCODE`)
- [ ] Sumber event #2: wrapper `sakura run <perintah>`
- [ ] Sumber event #3: ekstensi VS Code kecil (debug exception / task gagal)

## 3. Router coding

- [ ] Deteksi permintaan coding (kata kunci dulu, nanti klasifikasi dengan model kecil)
- [ ] Kirim permintaan coding ke model coding (API tier gratis / model lokal), dan jangan kirim rahasia
- [ ] Kode tampil sebagai teks di frontend; Sakura hanya membacakan ringkasan pendek

## 4. LLM Sakura (fine-tune): DIHENTIKAN (2026-11-20)

GPU T4 di Colab/Kaggle tidak kuat menjalankan fine-tune Qwen3-4B. Sakura tetap memakai model dasar `qwen/qwen3-4b-2507` + system prompt Jepang (`source/system_prompt.txt`), yang hasilnya sudah lebih baik dari v1.

- [x] Fine-tune v1, hasilnya kalah dari model dasar + prompt Jepang (sekarang `.env` memakai `qwen/qwen3-4b-2507`)
- [x] Notebook v2 diperbaiki (`tools/finetune/sft_qlora_sakura_colab.ipynb`): buang `<think>`, user Indonesia/Jepang, filter terjemahan, eval vs baseline
- ~~Jalankan v2 di Colab/Kaggle → kirim hasil sel 9 (BASELINE vs FINETUNED)~~ (dihentikan: T4 tidak kuat)
- ~~Kalau v2 menang, pasang GGUF v2 di LM Studio dan ubah `LM_STUDIO_MODEL`~~ (dihentikan)
- [ ] Atribusi dataset CC-BY-4.0 (scryptiam/anime-waifu-personality-chat) & cek lisensi dataset lain. Hanya perlu kalau model v1 atau dataset-nya dibagikan

## 5. Avatar 3D

- [ ] Rapikan pemakaian `Character/OG/sakura_.vrm` di `three-canvas`
- [ ] Ekspresi/animasi dipicu dari WebSocket (`{"expression": "angry"}` / `"happy"`)
- [ ] Lip-sync dari audio balasan

## 6. Rapikan kode

- [ ] Pipeline memori (`handle_user_iput`, `process_chat_llm` dengan intent/cache) ditulis setelah `uvicorn.run(...)` di `api_server.py`, jadi tidak pernah jalan. Sambungkan ke chat atau hapus
- [ ] Batasi mount statis `/Assets` (sekarang ikut membuka `Assets/book_train`, 187 MB data training)
- [ ] Tinjau `/api/chat_db` (data keuangan) sebelum server dibuka untuk orang lain

## 7. Tahap 2 & 3 (nanti)

- [ ] Pecah `api_server.py` → gateway (ringan) + worker (LLM, TTS, Whisper)
- [ ] Worker mengirim audio sebagai bytes ke gateway (bukan menulis file lokal)
- [ ] Gateway di Oracle Always Free, frontend & model 3D di Cloudflare Pages
- [ ] Login sendiri di gateway (kalau tidak pakai Cloudflare Access)
- [ ] Server GPU 24 GB menggantikan laptop sebagai worker (kalau proyek makin serius)
