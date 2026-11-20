from flask import Flask, request, jsonify
import requests
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from LLM.llm_config import LLM_URL, get_headers, build_payload, clean_reply

# Konfigurasi Encoding
sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)
base_dir = os.path.dirname(os.path.abspath(__file__))

@app.route('/generate', methods=['POST'])
def generate():
    # 1. Menangkap teks dari Golang
    data = request.json
    pesan_user = data.get('text', '')

    if not pesan_user:
        return jsonify({"error": "Pesan kosong"}), 400

    # 2. Membaca System Prompt
    system_prompt = "Kamu adalah Alice, asisten virtual yang baik hati."
    try:
        # Menyesuaikan path agar mengarah ke folder prompt/system_prompt.txt
        prompt_path = os.path.join(base_dir, "..", "prompt", "system_prompt.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read()
    except FileNotFoundError:
        print("Peringatan: File system_prompt.txt tidak ditemukan, menggunakan prompt default.")

    # 3. Setup Payload untuk LM Studio / LLM Lokal
    # Menggunakan endpoint standar OpenAI: /v1/chat/completions
    base_url = LLM_URL
    
    # Format payload yang benar (menggunakan daftar "messages")
    payload = build_payload([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": pesan_user}
    ])
    headers = get_headers()

    # 4. Melakukan HTTP POST ke LLM Lokal
    try:
        res = requests.post(base_url, json=payload, headers=headers)
        res.raise_for_status() # Akan memicu error jika status bukan 200 OK
        data_llm = res.json()
        
        # Mengambil teks balasan dari format JSON OpenAI
        jawaban_ai = clean_reply(data_llm["choices"][0]["message"]["content"])
    except requests.exceptions.RequestException as e:
        print(f"Error koneksi ke LLM: {e}")
        jawaban_ai = "*Maaf, aku tidak bisa menghubungi server otakku (Port 1234 mati atau model belum dimuat).*"
    except KeyError as e:
        print(f"Error parsing JSON dari LLM: {e}")
        jawaban_ai = "*Format balasan dari otakku sepertinya salah.*"

    print(f"Sakura (ID): {jawaban_ai}")

    # ========================================================
    # TODO: Jika Anda ingin menyalakan Terjemahan (translator.py)
    # dan Text-to-Speech (voicefox.py), Anda bisa memasukkan 
    # kodenya di bagian ini sebelum return.
    # ========================================================

    # 5. Mengembalikan jawaban ke Golang
    return jsonify({"reply": jawaban_ai})

if __name__ == '__main__':
    print("🧠 Otak Python (Flask) menyala di port 8080...")
    # debug=False agar aman dari restart otomatis ganda di beberapa sistem
    app.run(port=8080, debug=False)

    #menyambunngkan ke Faiss_Vector.py
    from data.Faiss_Vector import db, embeddings