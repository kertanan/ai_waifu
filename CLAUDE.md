# Sakura (waifu AI): catatan untuk Claude

Sebelum mulai kerja, baca bagian **"Recap terakhir"** di [WORKFLOW.md](WORKFLOW.md) untuk kondisi proyek dan pekerjaan yang belum selesai. Daftar tugas lengkap ada di [TODO.md](TODO.md), rencana server di [DEPLOYMENT_ARCHITECTURE.md](DEPLOYMENT_ARCHITECTURE.md).

- User berbahasa Indonesia. Sakura sendiri menjawab dalam bahasa Jepang (tsundere).
- Jalankan Python proyek dengan `D:\python\python`, bukan venv `E:\mitm-env` yang aktif di terminal (paket `whisper` di sana salah).
- Saat tes, jangan nyalakan GPT-SoVITS kecuali diminta. VOICEVOX dipakai sebagai cadangan.
- `SYSTEM_PROMPT` di `tools/finetune/sft_qlora_sakura_colab.ipynb` harus sama dengan `source/system_prompt.txt`.
- Setelah menyelesaikan tugas, centang item di `TODO.md` dan perbarui "Recap terakhir" di `WORKFLOW.md`.
