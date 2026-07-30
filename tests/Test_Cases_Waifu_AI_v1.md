# 🧪 Dokumen Skenario Pengujian (Test Cases) - Waifu AI Assistant

Dokumen ini merangkum skenario pengujian sistem secara komprehensif untuk proyek **Waifu AI Assistant**. Pengujian difokuskan pada tiga aspek utama: **Payload** (Validasi Data Masukan/Keluaran), **Runtime** (Waktu Eksekusi/Performa), dan **Memory Efficiency** (Penggunaan Sumber Daya RAM).

---

## 📦 1. Pengujian Payload (Payload Testing)
Pengujian ini bertujuan untuk memastikan *endpoint* API (`/api/chat` dan `/api/voice-chat`) dapat menangani berbagai jenis data masukan (payload) dengan benar, baik data yang valid, tidak valid, maupun data ekstrem (edge cases).

| Test ID | Skenario Pengujian | Endpoint | Pre-kondisi | Payload / Input | Hasil yang Diharapkan (Expected Result) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-P01** | Valid Text Payload | `POST /api/chat` | Server berjalan, LLM & TTS *online*. | `{"chat": "Halo Sakura!", "number": 1}` | Status `200 OK`. Mengembalikan JSON berisi `{"balasan": "...", "audio": "..."}`. |
| **TC-P02** | Missing/Empty Payload | `POST /api/chat` | Server berjalan. | `{}` atau `{"chat": "", "number": null}` | Status `422 Unprocessable Entity` atau `400 Bad Request`. Server tidak *crash*. |
| **TC-P03** | Injection/Special Chars | `POST /api/chat` | Server berjalan. | `{"chat": "DROP TABLE interaksi_utama;", "number": 1}` | Status `200 OK`. Sistem mengenali sebagai teks biasa (ngobrol_biasa) dan tidak mengeksekusi SQL. |
| **TC-P04** | Valid Audio Payload | `POST /api/voice-chat` | Whisper *online*. | File `audio.webm` (durasi 5 detik, suara manusia). | Status `200 OK`. Mengembalikan hasil transkripsi dan balasan dari LLM. |
| **TC-P05** | Large/Invalid Audio File | `POST /api/voice-chat` | Server berjalan. | File `.mp4` 50MB atau file `.txt` yang di-*rename* jadi `.webm`. | Status `415 Unsupported Media Type` atau `400 Bad Request`. Menolak pemrosesan. |
| **TC-P06** | Financial Intent Payload | `POST /api/chat` | Database terhubung. | `{"chat": "aku baru aja jajan boba 25000", "number": 1}` | Status `200 OK`. Intent `keuangan_keluar` terdeteksi, data masuk ke tabel `data_keuangan`. |

---

## ⏱️ 2. Pengujian Waktu Eksekusi (Runtime Testing)
Pengujian ini mengukur latensi dan kecepatan respons dari berbagai komponen sistem. Target utamanya adalah menjaga interaksi agar tetap terasa *real-time* atau natural bagi pengguna.

| Test ID | Skenario Pengujian | Komponen yang Diuji | Metodologi & Alat | Target (SLA) | Hasil yang Diharapkan |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-R01** | End-to-End Chat Latency | Seluruh Sistem | Menggunakan `time` module di klien untuk mengukur jeda dari *request* dikirim hingga *response* diterima. | `< 5 Detik` | Proses (Deteksi Intent + LLM + TTS) selesai dalam waktu kurang dari 5 detik. |
| **TC-R02** | LLM Inference Time | LLM (Granite) / LM Studio | Merekam *timestamp* sebelum dan sesudah *request* ke `localhost:1234`. | `< 2 Detik` | LLM menghasilkan respons teks (*max 150 tokens*) dalam waktu < 2 detik. |
| **TC-R03** | TTS Generation Time | Voicevox | Merekam waktu eksekusi skrip `voicefox.py`. | `< 1.5 Detik` | Sintesis teks ke file `reply.wav` memakan waktu kurang dari 1.5 detik per kalimat. |
| **TC-R04** | STT (Whisper) Runtime | Whisper (Base Model) | Mengirim audio berdurasi 10 detik dan mencatat waktu transkripsi. | `< 2 Detik` | Transkripsi selesai cepat karena menggunakan CPU inference pada model `base`. |
| **TC-R05** | Database Query Speed | SQLite (db_connect) | Menggunakan modul `timeit` pada fungsi *insert* dan *select* di database. | `< 50 ms` | Pencatatan memori atau data keuangan terjadi secara instan tanpa memblokir *thread* utama. |

---

## 🧠 3. Pengujian Efisiensi Memori (Memory Efficiency Testing)
Karena sistem ini menggabungkan model AI (LLM, Whisper) dan server dalam satu lingkungan, manajemen memori menjadi krusial untuk mencegah *memory leak* atau *Out of Memory (OOM)*.

| Test ID | Skenario Pengujian | Fokus Pengujian | Metodologi & Alat | Hasil yang Diharapkan |
| :--- | :--- | :--- | :--- | :--- |
| **TC-M01** | API Server Baseline Memory | FastAPI | Menggunakan *library* `memory_profiler` (`@profile`) pada fungsi utama `proses_chat_llm()`. | Penggunaan RAM stabil saat *idle* (hanya memuat *library* dasar, tanpa model berat). |
| **TC-M02** | Memory Leak Stress Test | Seluruh Sistem | Mengirim 100 *request* beruntun via *script loop*, memantau grafik RAM via *Task Manager* atau `psutil`. | RAM naik saat proses berjalan, tetapi **kembali turun (garbage collected)** setelah respons dikirim. Tidak ada tren kenaikan permanen. |
| **TC-M03** | SQLite Connection Leak | Database Module | Membuka koneksi, mengirim data, lalu mengecek jumlah koneksi aktif. | Setiap koneksi ke `database.db` langsung ditutup (`.close()`) atau di-*release* setelah *query* selesai. |
| **TC-M04** | File I/O Memory Impact | Audio Processing | Memantau memori saat membaca/menulis `reply.wav` dan *file* audio dari klien berulang kali. | File ditimpa (di-*overwrite*) dengan benar dan *buffer* dibersihkan dari memori setelah konversi selesai. |

---

## 🛠️ Panduan Implementasi Pengujian Otomatis

Untuk mengotomatisasi *test cases* di atas, Anda dapat menggunakan *stack* pengujian berikut di dalam Python:

1. **Payload Testing:** Gunakan `pytest` dan `httpx` (atau `requests`).
2. **Runtime Testing:** Gunakan `time.perf_counter()` di dalam *fixture* pytest.
3. **Memory Testing:** Gunakan *library* `memory_profiler` dan `psutil`.

**Contoh Skrip Singkat (Kombinasi Payload & Runtime):**
```python
import pytest
import requests
import time

def test_chat_payload_and_runtime():
    url = "http://localhost:8080/api/chat"
    payload = {"chat": "Cek keuangan aku dong", "number": 1}
    
    start_time = time.perf_counter()
    response = requests.post(url, json=payload)
    end_time = time.perf_counter()
    
    # 1. Test Payload (Status dan Struktur)
    assert response.status_code == 200
    assert "balasan" in response.json()
    
    # 2. Test Runtime (Di bawah 3 detik)
    execution_time = end_time - start_time
    assert execution_time < 3.0, f"Runtime terlalu lambat: {execution_time} detik"
```
