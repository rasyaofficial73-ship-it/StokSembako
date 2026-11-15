
import sqlite3

db = sqlite3.connect("sembako_bersama.db")

# Tampilkan data beras yang tersedia
beras = db.execute("""
    SELECT id, nama, satuan, stok
    FROM barang
    WHERE LOWER(nama) = 'beras'
""").fetchall()

print("Data beras saat ini:")
for item in beras:
    print(item)

if len(beras) == 1:
    db.execute("""
        UPDATE barang
        SET satuan = 'liter'
        WHERE id = ?
    """, (beras[0][0],))

    db.commit()
    print("Berhasil! Satuan beras sekarang menjadi liter.")

elif len(beras) == 0:
    print("Data beras tidak ditemukan.")

else:
    print("Ada lebih dari satu data beras. Tidak ada perubahan.")

db.close()
