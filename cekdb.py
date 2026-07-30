import sqlite3

# Sambungkan ke file database buatanmu
db = sqlite3.connect("database.db")
cursor = db.cursor()

print("=== CEK TABEL DATA KEUANGAN ===")
# Mengambil semua isi tabel keuangan
cursor.execute("SELECT * FROM data_keuangan")
data = cursor.fetchall()

for baris in data:
    print(baris)

db.close()