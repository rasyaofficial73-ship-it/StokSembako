
import os
import sqlite3
from functools import wraps
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, g
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "ganti-secret-key-untuk-lokal")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "sembako_bersama.db")


# ---------- DATABASE ----------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.execute("PRAGMA foreign_keys = ON")

    db.executescript("""
    
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        nama TEXT NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'karyawan')),
        bio TEXT NOT NULL DEFAULT '',
        aktif INTEGER NOT NULL DEFAULT 1,
        dibuat TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS barang (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nama TEXT UNIQUE NOT NULL,
        kategori TEXT NOT NULL DEFAULT 'Sembako',
        stok INTEGER NOT NULL DEFAULT 0 CHECK(stok >= 0),
        satuan TEXT NOT NULL DEFAULT 'pcs',
        harga REAL NOT NULL DEFAULT 0 CHECK(harga >= 0)
    );

    CREATE TABLE IF NOT EXISTS transaksi (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barang_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        jenis TEXT NOT NULL CHECK(jenis IN ('masuk', 'keluar')),
        jumlah INTEGER NOT NULL CHECK(jumlah > 0),
        keterangan TEXT NOT NULL DEFAULT '',
        waktu TEXT NOT NULL,
        FOREIGN KEY(barang_id) REFERENCES barang(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    jumlah_barang = db.execute(
        "SELECT COUNT(*) FROM barang"
    ).fetchone()[0]

    if jumlah_barang == 0:
        barang_awal = [
            ("Beras", "Sembako", 50, "kg", 15000),
            ("Gula Pasir", "Sembako", 30, "kg", 17000),
            ("Minyak Goreng", "Sembako", 40, "liter", 18000),
            ("Tepung Terigu", "Sembako", 25, "kg", 12000),
            ("Telur", "Sembako", 20, "kg", 28000),
            ("Garam", "Sembako", 30, "bungkus", 3000),
            ("Mie Instan", "Sembako", 100, "bungkus", 3500),
            ("Kecap Manis", "Sembako", 20, "botol", 12000),
            ("Susu Kental Manis", "Sembako", 20, "kaleng", 11000),
            ("Tepung Beras", "Sembako", 15, "kg", 14000),
            ("Kacang Hijau", "Sembako", 15, "kg", 18000),
            ("Bawang Putih", "Sembako", 10, "kg", 35000),
        ]

        db.executemany(
            """
            INSERT INTO barang (nama, kategori, stok, satuan, harga)
            VALUES (?, ?, ?, ?, ?)
            """,
            barang_awal
        )

    admin = db.execute(
        "SELECT id FROM users WHERE username = ?", ("admin",)
    ).fetchone()

    if admin is None:
        db.execute("""
            INSERT INTO users
            (username, nama, password, role, bio, aktif, dibuat)
            VALUES (?, ?, ?, 'admin', ?, 1, ?)
        """, (
            "admin",
            "Administrator",
            generate_password_hash("GantiAdmin123!"),
            "Administrator toko sembako",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

    db.commit()
    db.close()


# ---------- LOGIN DAN HAK AKSES ----------

@app.before_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = None

    if user_id is not None:
        g.user = get_db().execute(
            "SELECT * FROM users WHERE id = ? AND aktif = 1",
            (user_id,)
        ).fetchone()

        if g.user is None:
            session.clear()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for("index"))
        return view(*args, **kwargs)
    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash("Silakan login terlebih dahulu.", "warning")
            return redirect(url_for("login_admin"))

        if g.user["role"] != "admin":
            flash("Halaman ini hanya untuk admin.", "danger")
            return redirect(url_for("dashboard"))

        return view(*args, **kwargs)
    return wrapped_view


# ---------- HALAMAN LOGIN ----------

@app.route("/")
def index():
    if g.user:
        return redirect(url_for("dashboard"))
    return render_template("login.html", mode="pilih")


@app.route("/login_admin_sembako", methods=["GET", "POST"])
def login_admin():
    if g.user:
        if g.user["role"] == "admin":
            return redirect(url_for("dashboard"))
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = get_db().execute(
            """SELECT * FROM users
               WHERE username = ? AND role = 'admin' AND aktif = 1""",
            (username,)
        ).fetchone()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))

        flash("Username atau password admin salah.", "danger")

    return render_template("login.html", mode="admin")


@app.route("/login_karyawan_sembako", methods=["GET", "POST"])
def login_karyawan():
    if g.user:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = get_db().execute(
            """SELECT * FROM users
               WHERE username = ? AND role = 'karyawan' AND aktif = 1""",
            (username,)
        ).fetchone()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))

        flash("Username atau password karyawan salah.", "danger")

    return render_template("login.html", mode="karyawan")


@app.route("/logout")
def logout():
    session.clear()
    flash("Kamu telah logout.", "success")
    return redirect(url_for("index"))


# ---------- DASHBOARD ----------

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()

    jumlah_barang = db.execute(
        "SELECT COUNT(*) AS total FROM barang"
    ).fetchone()["total"]

    jumlah_karyawan = db.execute(
        "SELECT COUNT(*) AS total FROM users WHERE role='karyawan'"
    ).fetchone()["total"]

    total_stok = db.execute(
        "SELECT COALESCE(SUM(stok), 0) AS total FROM barang"
    ).fetchone()["total"]

    transaksi = db.execute("""
        SELECT t.*, b.nama AS nama_barang, u.nama AS nama_user
        FROM transaksi t
        JOIN barang b ON b.id = t.barang_id
        JOIN users u ON u.id = t.user_id
        ORDER BY t.id DESC LIMIT 10
    """).fetchall()

    return render_template(
        "dashboard.html",
        jumlah_barang=jumlah_barang,
        jumlah_karyawan=jumlah_karyawan,
        total_stok=total_stok,
        transaksi=transaksi
    )


# ---------- STOK BARANG ----------

@app.route("/stok", methods=["GET", "POST"])
@login_required
def stok():
    db = get_db()

    if request.method == "POST":
        if g.user["role"] != "admin":
            flash("Hanya admin yang boleh menambahkan data barang.", "danger")
            return redirect(url_for("stok"))

        nama = request.form.get("nama", "").strip()
        kategori = request.form.get("kategori", "Sembako").strip()
        satuan = request.form.get("satuan", "pcs").strip()

        try:
            stok_awal = int(request.form.get("stok", "0"))
            harga = float(request.form.get("harga", "0"))
            if not nama or stok_awal < 0 or harga < 0:
                raise ValueError
        except ValueError:
            flash("Nama, stok, atau harga tidak valid.", "danger")
            return redirect(url_for("stok"))

        try:
            db.execute(
                """INSERT INTO barang (nama, kategori, stok, satuan, harga)
                   VALUES (?, ?, ?, ?, ?)""",
                (nama, kategori, stok_awal, satuan, harga)
            )
            db.commit()
            flash("Barang berhasil ditambahkan.", "success")
        except sqlite3.IntegrityError:
            flash("Nama barang sudah ada atau data tidak valid.", "danger")

        return redirect(url_for("stok"))

    daftar_barang = db.execute(
        "SELECT * FROM barang ORDER BY nama"
    ).fetchall()

    return render_template("stok.html", barang=daftar_barang)


@app.route("/barang/hapus/<int:barang_id>", methods=["POST"])
@admin_required
def hapus_barang(barang_id):
    db = get_db()

    riwayat = db.execute(
        "SELECT id FROM transaksi WHERE barang_id = ? LIMIT 1",
        (barang_id,)
    ).fetchone()

    if riwayat:
        flash("Barang memiliki riwayat transaksi sehingga tidak bisa dihapus.", "danger")
    else:
        db.execute("DELETE FROM barang WHERE id = ?", (barang_id,))
        db.commit()
        flash("Barang berhasil dihapus.", "success")

    return redirect(url_for("stok"))


# ---------- TRANSAKSI BARANG MASUK/KELUAR ----------

@app.route("/transaksi", methods=["GET", "POST"])
@login_required
def transaksi():
    db = get_db()

    if request.method == "POST":
        try:
            barang_id = int(request.form.get("barang_id", "0"))
            jumlah = int(request.form.get("jumlah", "0"))
            jenis = request.form.get("jenis", "")
            keterangan = request.form.get("keterangan", "").strip()

            if jumlah <= 0 or jenis not in ("masuk", "keluar"):
                raise ValueError
        except ValueError:
            flash("Pilih barang dan masukkan jumlah yang valid.", "danger")
            return redirect(url_for("transaksi"))

        barang = db.execute(
            "SELECT * FROM barang WHERE id = ?", (barang_id,)
        ).fetchone()

        if barang is None:
            flash("Barang tidak ditemukan.", "danger")
            return redirect(url_for("transaksi"))

        if jenis == "keluar" and barang["stok"] < jumlah:
            flash("Stok tidak mencukupi untuk transaksi keluar.", "danger")
            return redirect(url_for("transaksi"))

        if jenis == "masuk":
            db.execute(
                "UPDATE barang SET stok = stok + ? WHERE id = ?",
                (jumlah, barang_id)
            )
        else:
            db.execute(
                "UPDATE barang SET stok = stok - ? WHERE id = ?",
                (jumlah, barang_id)
            )

        db.execute("""
            INSERT INTO transaksi
            (barang_id, user_id, jenis, jumlah, keterangan, waktu)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            barang_id,
            g.user["id"],
            jenis,
            jumlah,
            keterangan,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        db.commit()
        flash("Transaksi berhasil disimpan dan stok diperbarui.", "success")
        return redirect(url_for("transaksi"))

    daftar_barang = db.execute(
        "SELECT * FROM barang ORDER BY nama"
    ).fetchall()

    if g.user["role"] == "admin":
        riwayat = db.execute("""
            SELECT t.*, b.nama AS nama_barang, u.nama AS nama_user
            FROM transaksi t
            JOIN barang b ON b.id = t.barang_id
            JOIN users u ON u.id = t.user_id
            ORDER BY t.id DESC LIMIT 100
        """).fetchall()
    else:
        riwayat = db.execute("""
            SELECT t.*, b.nama AS nama_barang, u.nama AS nama_user
            FROM transaksi t
            JOIN barang b ON b.id = t.barang_id
            JOIN users u ON u.id = t.user_id
            WHERE t.user_id = ?
            ORDER BY t.id DESC LIMIT 100
        """, (g.user["id"],)).fetchall()

    return render_template(
        "transaksi.html",
        barang=daftar_barang,
        riwayat=riwayat
    )


# ---------- KELOLA AKUN KARYAWAN (ADMIN SAJA) ----------

@app.route("/pegawai", methods=["GET", "POST"])
@admin_required
def pegawai():
    db = get_db()

    if request.method == "POST":
        nama = request.form.get("nama", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not nama or not username or len(password) < 6:
            flash("Isi nama, username, dan password minimal 6 karakter.", "danger")
            return redirect(url_for("pegawai"))

        try:
            db.execute("""
                INSERT INTO users
                (username, nama, password, role, bio, aktif, dibuat)
                VALUES (?, ?, ?, 'karyawan', '', 1, ?)
            """, (
                username,
                nama,
                generate_password_hash(password),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            db.commit()
            flash("Akun karyawan berhasil dibuat.", "success")
        except sqlite3.IntegrityError:
            flash("Username sudah digunakan.", "danger")

        return redirect(url_for("pegawai"))

    daftar = db.execute("""
        SELECT u.*,
        (SELECT COUNT(*) FROM transaksi t WHERE t.user_id = u.id) AS total_transaksi
        FROM users u
        WHERE u.role = 'karyawan'
        ORDER BY u.nama
    """).fetchall()

    return render_template("pegawai.html", pegawai=daftar)


@app.route("/pegawai/status/<int:user_id>", methods=["POST"])
@admin_required
def status_pegawai(user_id):
    db = get_db()

    user = db.execute(
        "SELECT * FROM users WHERE id = ? AND role = 'karyawan'",
        (user_id,)
    ).fetchone()

    if user is None:
        flash("Karyawan tidak ditemukan.", "danger")
    else:
        status_baru = 0 if user["aktif"] else 1
        db.execute(
            "UPDATE users SET aktif = ? WHERE id = ?",
            (status_baru, user_id)
        )
        db.commit()
        flash("Status akun karyawan diperbarui.", "success")

    return redirect(url_for("pegawai"))


@app.route("/pegawai/<int:user_id>")
@admin_required
def detail_pegawai(user_id):
    db = get_db()

    user = db.execute(
        "SELECT * FROM users WHERE id = ? AND role = 'karyawan'",
        (user_id,)
    ).fetchone()

    if user is None:
        flash("Karyawan tidak ditemukan.", "danger")
        return redirect(url_for("pegawai"))

    riwayat = db.execute("""
        SELECT t.*, b.nama AS nama_barang
        FROM transaksi t JOIN barang b ON b.id = t.barang_id
        WHERE t.user_id = ?
        ORDER BY t.id DESC LIMIT 100
    """, (user_id,)).fetchall()

    return render_template(
        "profil.html", profil=user, riwayat=riwayat, mode="admin"
    )


# ---------- PROFIL PENGGUNA ----------

@app.route("/profil", methods=["GET", "POST"])
@login_required
def profil():
    db = get_db()

    if request.method == "POST":
        nama = request.form.get("nama", "").strip()
        bio = request.form.get("bio", "").strip()
        password_baru = request.form.get("password", "")

        if not nama:
            flash("Nama tidak boleh kosong.", "danger")
            return redirect(url_for("profil"))

        if password_baru and len(password_baru) < 6:
            flash("Password baru minimal 6 karakter.", "danger")
            return redirect(url_for("profil"))

        if password_baru:
            db.execute("""
                UPDATE users SET nama = ?, bio = ?, password = ?
                WHERE id = ?
            """, (
                nama, bio, generate_password_hash(password_baru), g.user["id"]
            ))
        else:
            db.execute(
                "UPDATE users SET nama = ?, bio = ? WHERE id = ?",
                (nama, bio, g.user["id"])
            )

        db.commit()
        flash("Profil berhasil diperbarui.", "success")
        return redirect(url_for("profil"))

    riwayat = db.execute("""
        SELECT t.*, b.nama AS nama_barang
        FROM transaksi t JOIN barang b ON b.id = t.barang_id
        WHERE t.user_id = ?
        ORDER BY t.id DESC LIMIT 30
    """, (g.user["id"],)).fetchall()

    return render_template(
        "profil.html", profil=g.user, riwayat=riwayat, mode="sendiri"
    )


# ---------- JALANKAN APLIKASI ----------

with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
