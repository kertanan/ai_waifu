import requests
import random
import os
import re

VOICEVOX_URL = "http://127.0.0.1:50021"

# =========================
# TEXT PREPROCESSING
# =========================
def preprocess_text(text):

    # Hapus teks di dalam kurung (biasanya tag ekspresi seperti "(tersenyum)" atau "(marah)")
    # agar mesin Voicevox tidak ikut membacanya secara kaku.
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'（[^）]*）', '', text)
    text = re.sub(r'\[[^\]]*\]', '', text)
    text = re.sub(r'【[^】]*】', '', text)

    # natural punctuation
    text = text.replace("...", "…")
    
    # Hapus spasi buatan karena spasi dalam bahasa Jepang justru merusak intonasi alami (MeCab parser) di mesin Voicevox

    # conversational tweak
    replacements = {
        "です。": "ですね。",
        "ます。": "ますね。",
        "はい。": "はい〜。",
        "わかりました": "わかりました〜",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


# =========================
# GENERATE AUDIO
# =========================
def generate_play_audio(
    text,
    voice="sakura",
    speed=1.0,
    pitch=0.0,
    speaker_jp=14, # 14 adalah ID untuk Meimei Himari (冥鳴ひまり)
    intonation=1.0, # 1.0 adalah settingan paling natural bawaan Voicevox
    volume=1.0
):

    processed_text = preprocess_text(text)

    print(
        f"[VOICEFOX] memproses suara '{processed_text}' "
        f"(speed={speed}, pitch={pitch}, intonation={intonation})"
    )

    try:

        # =========================
        # AUDIO QUERY
        # =========================
        response_query = requests.post(
            f"{VOICEVOX_URL}/audio_query",
            params={
                "text": processed_text,
                "speaker": speaker_jp
            }
        )

        if response_query.status_code != 200:
            print(f"[VOICEFOX] Error audio_query: {response_query.status_code}")
            return

        blueprint_voice = response_query.json()

        # =========================
        # NATURAL SETTINGS
        # =========================

        # Menggunakan skala stabil tanpa pengacakan agar karakter suaranya konsisten
        blueprint_voice["speedScale"] = speed
        blueprint_voice["pitchScale"] = pitch
        blueprint_voice["intonationScale"] = intonation

        blueprint_voice["volumeScale"] = volume

        # Membiarkan mesin Voicevox mengatur durasi pause secara otomatis (AI-driven)
        # tanpa dipaksa / di-override, sehingga terdengar jauh lebih natural.
        
        # =========================
        # SYNTHESIS
        # =========================
        response_synthesis = requests.post(
            f"{VOICEVOX_URL}/synthesis",
            params={"speaker": speaker_jp},
            json=blueprint_voice
        )

        if response_synthesis.status_code != 200:
            print(f"[VOICEFOX] Error synthesis: {response_synthesis.status_code}")
            return


        file_audio = r"voicefox_source\reply.wav"

        with open(file_audio, "wb") as f:
            f.write(response_synthesis.content)

        print(f"[VOICEFOX] Audio berhasil disimpan ke {file_audio}")
        return file_audio

    except requests.exceptions.RequestException as e:
        print(f"[VOICEFOX] Error koneksi: {e}")
        return



if __name__ == "__main__":

    teks_tes = """
    えっと〜…
    システム起動完了です。
    今日もよろしくお願いしますね、マスター。
    """

    generate_play_audio(
        teks_tes,
        speaker_jp=3,
        speed=0.95,
        pitch=-0.05,
        intonation=1.4
    )