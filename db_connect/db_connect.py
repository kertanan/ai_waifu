import functools
import sqlite3
import threading
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import uvicorn
import re

db = sqlite3.connect("database.db", check_same_thread=False)
cursor = db.cursor()

# Satu koneksi & cursor dipakai bersama oleh semua thread (rute FastAPI `def` berjalan di threadpool).
# Tanpa kunci, dua chat bersamaan bisa saling menimpa `cursor.lastrowid` / transaksi.
db_lock = threading.RLock()


def _locked(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        with db_lock:
            return fn(*args, **kwargs)
    return wrapper

def create_tables():
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS interaksi_utama(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pesan_user TEXT,
        intent TEXT,
        time DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS log_obrolan(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        interaksi_id INTEGER,
        respon_ai TEXT,
        time DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (interaksi_id) REFERENCES interaksi_utama(id)
        )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS data_keuangan(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        interaksi_id INTEGER,
        kategori TEXT,
        jumlah REAL,
        time DATETIME DEFAULT CURRENT_TIMESTAMP,
        keterangan TEXT,
        FOREIGN KEY (interaksi_id) REFERENCES interaksi_utama(id)
        )
    ''')
    db.commit()

create_tables()

# Setup Router (agar bisa di-import ke api_server.py)
router = APIRouter()

class PesanUser(BaseModel):
    teks: str

def deteksi_intent(teks: str) -> str:

    teks_lower = teks.lower()
    
    if any(keyword in teks_lower for keyword in ['beli', 'bayar', 'jajan', 'pengeluaran', 'belanja']):
        return 'keuangan_keluar'
        
    elif any(keyword in teks_lower for keyword in ['gajian', 'dapat uang', 'pemasukan', 'dikasih', 'nabung']):
        return 'keuangan_masuk'
        
    elif any(keyword in teks_lower for keyword in ['sisa uang', 'sisa saldo', 'cek uang', 'total pengeluaran']):
        return 'cek_keuangan'
        
    else:
        return 'ngobrol_biasa'

# Fungsi untuk mengekstrak angka/nominal dari chat (misal: "50.000" jadi 50000.0)
def extract_data_keuangan(teks: str) -> dict:
    # Hilangkan titik agar format 50.000 bisa dibaca sebagai 50000
    teks_bersih = teks.replace('.', '')
    angka_ditemukan = re.findall(r'\d+', teks_bersih)
    
    jumlah = 0.0
    if angka_ditemukan:
        jumlah = float(angka_ditemukan[-1]) # Ambil angka terakhir jika ada beberapa angka
        
    return {"kategori": "umum", "jumlah": jumlah, "tipe": "transaksi", "keterangan": teks}

# Fungsi untuk menghitung sisa saldo dengan menjumlahkan pemasukan dan mengurangkan pengeluaran
@_locked
def cek_keuangan(intent: str = "") -> str:
    try:
        # Hitung Pemasukan
        cursor.execute('''
            SELECT SUM(jumlah) FROM data_keuangan dk
            JOIN interaksi_utama iu ON dk.interaksi_id = iu.id
            WHERE iu.intent = 'keuangan_masuk'
        ''')
        pemasukan = cursor.fetchone()[0]
        pemasukan = pemasukan if pemasukan is not None else 0.0
        
        # Hitung Pengeluaran
        cursor.execute('''
            SELECT SUM(jumlah) FROM data_keuangan dk
            JOIN interaksi_utama iu ON dk.interaksi_id = iu.id
            WHERE iu.intent = 'keuangan_keluar'
        ''')
        pengeluaran = cursor.fetchone()[0]
        pengeluaran = pengeluaran if pengeluaran is not None else 0.0
        
        sisa = pemasukan - pengeluaran
        
        if intent == 'cek_keuangan':
            return f"Total pemasukanmu {pemasukan}, dan pengeluaranmu {pengeluaran}. Jadi sisa uang kamu sekarang adalah {sisa} sayang."

        if pemasukan == 0.0 and pengeluaran == 0.0:
            return "0"

        return str(sisa)
            
    except Exception as e:
        print("Error saat menghitung saldo:", e)
        return "0"

# Endpoint dipindah ke router
@router.post("/api/chat_db")
@_locked
def chat_sakura(request: PesanUser):
    try:
        pesan = request.teks
        intent_user = deteksi_intent(pesan)

        cursor.execute("INSERT INTO interaksi_utama(pesan_user, intent) VALUES (?,?)", [pesan, intent_user])
        parent_id = cursor.lastrowid

        jawaban_final = ""

        if intent_user == 'keuangan_keluar':
            data = extract_data_keuangan(pesan)
            cursor.execute('''
            INSERT INTO data_keuangan (interaksi_id, kategori, jumlah, keterangan)
            VALUES (?,?,?,?)
            ''', [parent_id, data['kategori'], data['jumlah'], pesan])
            db.commit()
            jawaban_final = f"バ、バカじゃないの！？あんたのデータは{data['tipe']}で、{data['keterangan']}よ。合計は{data['jumlah']}なんだからね！これで何か買うつもりなら、絶対に無駄遣いしないでよね！べ、別に心配してるわけじゃないんだからね！"
            
        elif intent_user == 'keuangan_masuk':
            data = extract_data_keuangan(pesan)
            cursor.execute('''
            INSERT INTO data_keuangan (interaksi_id, kategori, jumlah, keterangan)
            VALUES (?,?,?,?)
            ''', [parent_id, data['kategori'], data['jumlah'], pesan])
            db.commit()
            jawaban_final = "ふん！ちゃんと貯金できたのね。えらいわ…っ、て、勘違いしないでよね！べ、別に褒めてなんかないんだからね！これからもちゃんと貯めなさいよ、バカ！"
            
        elif intent_user == 'cek_keuangan':
            jawaban_final = str(cek_keuangan(intent_user))
            
        elif intent_user == 'ngobrol_biasa':
            jawaban_final = "うるさいわね…ちゃんと聞いてるわよ！何度も言わせないでよね、バカ！"

        cursor.execute("INSERT INTO log_obrolan (interaksi_id, respon_ai) VALUES (?,?)", [parent_id, jawaban_final])
        db.commit()

        return {
            "status": "sukses",
            "intent": intent_user,
            "pesan_user": pesan,
            "respon_sakura": jawaban_final
        }
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@_locked
def proses_pesan_utama(pesan: str) -> dict:
    try:
        intent_user = deteksi_intent(pesan)
        if intent_user == 'ngobrol_biasa':
            return {"handled": False, "intent": intent_user}
            
        cursor.execute("INSERT INTO interaksi_utama(pesan_user, intent) VALUES (?,?)", [pesan, intent_user])
        parent_id = cursor.lastrowid
        
        jawaban_final = ""
        if intent_user == 'keuangan_keluar':
            data = extract_data_keuangan(pesan)
            cursor.execute('''INSERT INTO data_keuangan (interaksi_id, kategori, jumlah, keterangan) VALUES (?,?,?,?)''', 
                           [parent_id, data['kategori'], data['jumlah'], pesan])
            db.commit() # Commit dulu agar saldo ter-update
            sisa_saldo = cek_keuangan()
            jawaban_final = f"ねえ、あなた、さっき出したばかりじゃないの？ {data['jumlah']}. 現在の残高はあと {sisa_saldo}. 無駄遣いはしないでね！"
            
        elif intent_user == 'keuangan_masuk':
            data = extract_data_keuangan(pesan)
            cursor.execute('''INSERT INTO data_keuangan (interaksi_id, kategori, jumlah, keterangan) VALUES (?,?,?,?)''', 
                           [parent_id, data['kategori'], data['jumlah'], pesan])
            db.commit()
            sisa_saldo = cek_keuangan()
            jawaban_final = f"愛しい人、これだけの金額を貯金してくれてありがとう {data['jumlah']}. 現在の残高は {sisa_saldo}."
            
        elif intent_user == 'cek_keuangan':
            jawaban_final = cek_keuangan(intent_user)
            
        cursor.execute("INSERT INTO log_obrolan (interaksi_id, respon_ai) VALUES (?,?)", [parent_id, jawaban_final])
        db.commit()
        return {"handled": True, "jawaban": jawaban_final, "intent": intent_user}
    except Exception as e:
        db.rollback()
        print("DB Error:", e)
        return {"handled": False, "intent": "error"}

@_locked
def simpan_log_llm(pesan: str, respon_ai: str):
    try:
        cursor.execute("INSERT INTO interaksi_utama(pesan_user, intent) VALUES (?,?)", [pesan, 'ngobrol_biasa'])
        parent_id = cursor.lastrowid
        cursor.execute("INSERT INTO log_obrolan (interaksi_id, respon_ai) VALUES (?,?)", [parent_id, respon_ai])
        db.commit()
    except Exception as e:
        db.rollback()
        print("DB Error (simpan_log_llm):", e)