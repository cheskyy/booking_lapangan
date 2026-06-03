import json
import os

from flask import Flask, render_template, request, redirect, session, flash
import pymysql
from functools import wraps

app = Flask(__name__)
app.secret_key = "booking123"

# Konfigurasi MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''  # kosong jika XAMPP default
app.config['MYSQL_DB'] = 'booking_lapangan'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

def get_db():
    return pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB'],
        cursorclass=pymysql.cursors.DictCursor
    )

BASE_DIR = os.path.dirname(__file__)
USERS_FILE = os.path.join(BASE_DIR, "users.json")


def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # fallback defaults
    return {
        "admin": {"password": "123", "role": "admin"},
        "pegawai": {"password": "123", "role": "pegawai"},
        "pengurus": {"password": "123", "role": "pengurus"},
    }


def save_users(users_data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_data, f, indent=2)


users = load_users()

def login_required(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_role = session.get("role")
            # jika belum login -> redirect ke login
            if not user_role:
                return redirect("/")
            # admin memiliki akses ke semua route yang dilindungi
            if user_role != role and user_role != "admin":
                return redirect("/")
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ── AUTH ──────────────────────────────────────────
@app.route("/")
def login():
    if session.get("role"):
        if session["role"] == "user":
            return redirect("/booking")
        return redirect(f"/{session['role']}")
    return render_template("login.html")

@app.route("/cek_login", methods=["POST"])
def cek_login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    user = users.get(username)
    if user and user["password"] == password:
        session["username"] = username
        session["role"] = user["role"]
        if user["role"] == "user":
            return redirect("/booking")
        return redirect(f"/{user['role']}")
    flash("Username atau password salah.")
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = "user"

        if not username or not password:
            flash("Username dan password wajib diisi.")
            return redirect("/register")

        if username in users:
            flash("Username sudah terdaftar.")
            return redirect("/register")

        users[username] = {"password": password, "role": role}
        try:
            save_users(users)
        except Exception:
            pass

        flash("Registrasi berhasil. Silakan login.")
        return redirect("/")

    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ── ADMIN FEATURES ─────────────────────────────────
@app.route("/admin/users", methods=["GET", "POST"])
@login_required("admin")
def admin_users():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "pegawai")

        if not username or not password:
            flash("Username dan password tidak boleh kosong.")
            return redirect("/admin/users")

        users[username] = {"password": password, "role": role}
        save_users(users)
        flash(f"Akun {username} berhasil disimpan.")
        return redirect("/admin/users")

    return render_template("admin_users.html", users=users)


@app.route("/admin/users/delete/<username>")
@login_required("admin")
def admin_delete_user(username):
    if username == session.get("username"):
        flash("Anda tidak bisa menghapus akun yang sedang login.")
    elif username in users:
        users.pop(username)
        save_users(users)
        flash(f"Akun {username} berhasil dihapus.")
    else:
        flash("Akun tidak ditemukan.")
    return redirect("/admin/users")


@app.route("/admin/laporan")
@login_required("admin")
def admin_laporan():
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS total FROM bookings")
        total_booking = cur.fetchone().get("total", 0)

        cur.execute("SELECT role_pemesan, COUNT(*) AS total FROM bookings GROUP BY role_pemesan")
        total_per_role = cur.fetchall()

        cur.execute("SELECT nama_lapangan, COUNT(*) AS total FROM bookings GROUP BY nama_lapangan")
        total_per_lapangan = cur.fetchall()

        cur.execute("SELECT tanggal, COUNT(*) AS total FROM bookings GROUP BY tanggal ORDER BY tanggal DESC LIMIT 10")
        total_per_tanggal = cur.fetchall()
    finally:
        conn.close()

    return render_template(
        "laporan.html",
        total_booking=total_booking,
        total_per_role=total_per_role,
        total_per_lapangan=total_per_lapangan,
        total_per_tanggal=total_per_tanggal,
    )


# ── KELOLA LAPANGAN (admin) ─────────────────────────
@app.route("/admin/lapangan", methods=["GET", "POST"])
@login_required("admin")
def admin_lapangan():
    conn = get_db()
    try:
        cur = conn.cursor()

        if request.method == "POST":
            nama = request.form.get("nama_lapangan", "").strip()
            deskripsi = request.form.get("deskripsi", "").strip()
            if not nama:
                flash("Nama lapangan tidak boleh kosong.")
                return redirect("/admin/lapangan")
            cur.execute(
                "INSERT INTO lapangan (nama_lapangan, deskripsi) VALUES (%s, %s)",
                (nama, deskripsi),
            )
            conn.commit()
            flash("Lapangan berhasil ditambahkan.")
            return redirect("/admin/lapangan")

        cur.execute("SELECT * FROM lapangan ORDER BY id DESC")
        lapangans = cur.fetchall()
    finally:
        conn.close()

    return render_template("admin_lapangan.html", lapangans=lapangans)


@app.route("/admin/lapangan/delete/<int:id>")
@login_required("admin")
def admin_lapangan_delete(id):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM lapangan WHERE id = %s", (id,))
        conn.commit()
    finally:
        conn.close()

    flash("Lapangan berhasil dihapus.")
    return redirect("/admin/lapangan")


# ── DASHBOARD ─────────────────────────────────────
@app.route("/admin")
@login_required("admin")
def admin():
    return render_template("admin.html")

@app.route("/pegawai")
@login_required("pegawai")
def pegawai():
    return render_template("pegawai.html")

@app.route("/pengurus")
@login_required("pengurus")
def pengurus():
    return render_template("pengurus.html")

# ── BOOKING ───────────────────────────────────────
@app.route("/booking", methods=["GET", "POST"])
def booking():
    if not session.get("role"):
        return redirect("/")

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM lapangan ORDER BY nama_lapangan")
        lapangans = cur.fetchall()

        if request.method == "POST":
            nama_pemesan  = session.get("username")
            nama_lapangan = request.form.get("nama_lapangan", "").strip()
            tanggal       = request.form.get("tanggal", "")
            jam_mulai     = request.form.get("jam_mulai", "")
            jam_selesai   = request.form.get("jam_selesai", "")
            catatan       = request.form.get("catatan", "").strip()
            role_pemesan  = session.get("role")

            if not nama_lapangan or not tanggal or not jam_mulai or not jam_selesai:
                flash("Semua data booking harus diisi.")
                return redirect("/booking")

            if jam_mulai >= jam_selesai:
                flash("Jam mulai harus lebih awal dari jam selesai.")
                return redirect("/booking")

            cur.execute(
                "SELECT COUNT(*) AS count FROM bookings WHERE nama_lapangan = %s AND tanggal = %s "
                "AND status IN ('Menunggu Persetujuan', 'Disetujui (ACC)') "
                "AND jam_mulai < %s AND jam_selesai > %s",
                (nama_lapangan, tanggal, jam_selesai, jam_mulai),
            )
            conflict = cur.fetchone().get("count", 0)
            if conflict:
                flash("Lapangan sudah tidak tersedia pada jadwal tersebut.")
                return redirect("/booking")

            cur.execute(
                "INSERT INTO bookings "
                "(nama_pemesan, nama_lapangan, tanggal, jam_mulai, jam_selesai, catatan, role_pemesan, status) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (nama_pemesan, nama_lapangan, tanggal, jam_mulai, jam_selesai, catatan, role_pemesan, "Menunggu Persetujuan"),
            )
            conn.commit()
            flash("Booking berhasil disimpan dan menunggu persetujuan.")
            return redirect("/riwayat")

    finally:
        conn.close()

    return render_template("booking.html", lapangans=lapangans)

# ── LAPANGAN / JADWAL ─────────────────────────────
@app.route("/lapangan")
def lapangan():
    if not session.get("role"):
        return redirect("/")

    tanggal = request.args.get("tanggal")
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM lapangan ORDER BY nama_lapangan")
        lapangans = cur.fetchall()

        if tanggal:
            cur.execute(
                "SELECT * FROM bookings WHERE tanggal = %s ORDER BY nama_lapangan, jam_mulai",
                (tanggal,),
            )
            bookings = cur.fetchall()
        else:
            bookings = []
    finally:
        conn.close()

    field_schedule = []
    for lap in lapangans:
        field_bookings = [b for b in bookings if b["nama_lapangan"] == lap["nama_lapangan"]]
        if not field_bookings:
            status = "Tersedia"
        else:
            active = any(b["status"] in ["Menunggu Persetujuan", "Disetujui (ACC)"] for b in field_bookings)
            status = "Terisi" if active else "Tersedia"
        field_schedule.append({
            "lapangan": lap,
            "status": status,
            "bookings": field_bookings,
        })

    return render_template("lapangan.html", tanggal=tanggal, field_schedule=field_schedule)

# ── RIWAYAT ───────────────────────────────────────
@app.route("/riwayat")
def riwayat():
    if not session.get("role"):
        return redirect("/")

    conn = get_db()
    try:
        cur = conn.cursor()

        if session.get("role") == "user":
            cur.execute("""
                SELECT * FROM bookings
                WHERE nama_pemesan = %s
                ORDER BY created_at DESC
            """, (session.get("username"),))
        else:
            cur.execute("SELECT * FROM bookings ORDER BY created_at DESC")

        data = cur.fetchall()
    finally:
        conn.close()

    return render_template("riwayat.html", bookings=data)

@app.route("/booking/status/<int:id>", methods=["POST"])
def update_booking_status(id):
    if session.get("role") not in ["admin", "pengurus"]:
        return redirect("/")

    action = request.form.get("action")
    status_map = {
        "acc": "Disetujui (ACC)",
        "ditolak": "Ditolak",
        "selesai": "Selesai",
        "batal": "Dibatalkan",
    }
    new_status = status_map.get(action)
    if not new_status:
        flash("Aksi tidak dikenal.")
        return redirect("/riwayat")

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE bookings SET status = %s WHERE id = %s", (new_status, id))
        conn.commit()
    finally:
        conn.close()

    flash(f"Status booking berhasil diubah menjadi {new_status}.")
    return redirect("/riwayat")

@app.route("/booking/cancel/<int:id>", methods=["POST"])
def cancel_booking(id):
    if not session.get("role"):
        return redirect("/")

    conn = get_db()
    try:
        cur = conn.cursor()
        if session.get("role") == "user":
            cur.execute("SELECT nama_pemesan FROM bookings WHERE id = %s", (id,))
            booking = cur.fetchone()
            if not booking or booking["nama_pemesan"] != session.get("username"):
                flash("Akses ditolak.")
                return redirect("/riwayat")
        cur.execute("UPDATE bookings SET status = %s WHERE id = %s", ("Dibatalkan", id))
        conn.commit()
    finally:
        conn.close()

    flash("Booking dibatalkan.")
    return redirect("/riwayat")

# ── HAPUS BOOKING (admin only) ────────────────────
@app.route("/hapus/<int:id>")
@login_required("admin")
def hapus(id):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM bookings WHERE id = %s", (id,))
        conn.commit()
    finally:
        conn.close()
    flash("Booking berhasil dihapus.")
    return redirect("/riwayat")

if __name__ == "__main__":
    app.run(debug=True)