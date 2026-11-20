@echo off
REM Menyalakan server GPT-SoVITS (api_v2) di http://127.0.0.1:9880 untuk speech/voicefox.py
REM Ubah baris di bawah ke folder hasil ekstrak paket GPT-SoVITS Windows (versi v2pro).
set GPT_SOVITS_DIR=E:\GPT-SoVITS-v2pro-20250604

cd /d "%GPT_SOVITS_DIR%" || (echo Folder tidak ditemukan: %GPT_SOVITS_DIR% & pause & exit /b 1)
runtime\python.exe api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
pause
