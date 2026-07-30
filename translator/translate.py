from deep_translator import google_translator

def translate_text_to_japan(text_indonesia): 
    print(f"TRANSLATOR] Menerjemahkan teks '{text_indonesia}' ke bahasa Jepang...")
    try : 
        terjemahan = google_translator(source = 'id',target = 'ja').translate(text_indonesia)
        print(f"TRANSLATOR] Hasil terjemahan: '{terjemahan}'")
        return terjemahan
    except Exception as e:
        print(f"TRANSLATOR] Error saat menerjemahkan: {e}")
    
    #terjemahan cadangan jika terjadi error
    try : 
        terjemahan_cadangan = google_translator(source = 'id',target = 'ja').translate(text_indonesia)
        print(f"TRANSLATOR] Hasil terjemahan cadangan: '{terjemahan_cadangan}'")
        return terjemahan_cadangan
    except Exception as e: 
        print(f"TRANSLATOR] Error saat menerjemahkan dengan cadangan: {e}")
        return "エラーが発生しました"
    
# Blok pengujian: Hanya berjalan jika kamu me-run file ini langsung
if __name__ == "__main__":
    teks_uji = "Halo, bagaimana kabarmu hari ini?"
    hasil_terjemahan = translate_text_to_japan(teks_uji)
    print(f"Hasil terjemahan: {hasil_terjemahan}")