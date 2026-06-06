import os
import pymysql
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, session, flash
from functools import wraps
from flask_wtf import CSRFProtect

from config import Config
from user_utils import get_user, create_user, verify_password, list_users, delete_user, update_user, migrate_json_users


app = Flask(__name__)
app.config.from_object(Config)

# Session & cookie hardening
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,  # set True in production with HTTPS
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=60),
)

csrf = CSRFProtect(app)

# migrate users.json into DB if running init
try:
    migrate_json_users()
except Exception:
    pass


def get_db():
    return pymysql.connect(
        host=app.config.get('MYSQL_HOST', 'localhost'),
        user=app.config.get('MYSQL_USER', 'root'),
        password=app.config.get('MYSQL_PASSWORD', ''),
        database=app.config.get('MYSQL_DB', 'booking_lapangan'),
        cursorclass=pymysql.cursors.DictCursor,
    )

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
    user = get_user(username)
    if user and verify_password(user.get('password'), password):
        session.permanent = True
        session["username"] = username
        session["role"] = user.get("role")
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

        if get_user(username):
            flash("Username sudah terdaftar.")
            return redirect("/register")

        try:
            create_user(username, password, role)
        except Exception:
            flash("Gagal membuat akun, coba lagi.")
            return redirect("/register")

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
        try:
            create_user(username, password, role)
            flash(f"Akun {username} berhasil disimpan.")
        except Exception as e:
            flash(f"Gagal menyimpan akun: {e}")
        return redirect("/admin/users")
    users_data = list_users()
    return render_template("admin_users.html", users=users_data)


@app.route("/admin/users/delete/<username>")
@login_required("admin")
def admin_delete_user(username):
    if username == session.get("username"):
        flash("Anda tidak bisa menghapus akun yang sedang login.")
        return redirect("/admin/users")

    u = get_user(username)
    if not u:
        flash("Akun tidak ditemukan.")
        return redirect("/admin/users")

    delete_user(username)
    flash(f"Akun {username} berhasil dihapus.")
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


@app.route('/admin/users/edit/<username>', methods=['GET', 'POST'])
@login_required('admin')
def admin_edit_user(username):
    u = get_user(username)
    if not u:
        flash('User tidak ditemukan.')
        return redirect('/admin/users')

    if request.method == 'POST':
        password = request.form.get('password', '')
        role = request.form.get('role', u.get('role'))

        try:
            if password:
                update_user(username, password=password, role=role)
            else:
                update_user(username, role=role)
            flash('User berhasil diupdate.')
        except Exception as e:
            flash(f'Gagal mengupdate user: {e}')
        return redirect('/admin/users')

    return render_template('admin_edit_user.html', user=u)


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
    query_date = None
    if tanggal:
        try:
            query_date = datetime.strptime(tanggal, "%Y-%m-%d").date()
        except ValueError:
            app.logger.warning("Invalid tanggal format received: %s", tanggal)
            query_date = None

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM lapangan ORDER BY nama_lapangan")
        lapangans = cur.fetchall()

        bookings = []
        if query_date:
            query = (
                "SELECT * FROM bookings "
                "WHERE tanggal = %s "
                "ORDER BY nama_lapangan, jam_mulai"
            )
            app.logger.debug("Executing bookings query: %s with date=%s", query, query_date)
            cur.execute(query, (query_date,))
            bookings = cur.fetchall()
            app.logger.debug("Bookings rows found: %d", len(bookings))
            for book in bookings:
                app.logger.debug("Booking row: %s", book)
    finally:
        conn.close()

    field_schedule = []
    seen_lapangan_names = set()
    for lap in lapangans:
        lap_name = lap["nama_lapangan"].strip().lower()
        field_bookings = [b for b in bookings if b["nama_lapangan"].strip().lower() == lap_name]
        seen_lapangan_names.add(lap_name)
        active_bookings = [b for b in field_bookings if b["status"] not in ["Ditolak", "Dibatalkan"]]
        status = "Terisi" if active_bookings else "Tersedia"
        field_schedule.append({
            "lapangan": lap,
            "status": status,
            "bookings": active_bookings if active_bookings else field_bookings,
        })

    # Include any booking entries for lapangan names that are not present in the lapangan table.
    missing_lapangans = {b["nama_lapangan"].strip().lower() for b in bookings} - seen_lapangan_names
    for missing_name in missing_lapangans:
        matched_bookings = [b for b in bookings if b["nama_lapangan"].strip().lower() == missing_name]
        active_bookings = [b for b in matched_bookings if b["status"] not in ["Ditolak", "Dibatalkan"]]
        field_schedule.append({
            "lapangan": {"nama_lapangan": matched_bookings[0]["nama_lapangan"]},
            "status": "Terisi" if active_bookings else "Tersedia",
            "bookings": active_bookings if active_bookings else matched_bookings,
        })

    app.logger.debug("Field schedule entries: %d", len(field_schedule))
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

@app.route("/dashboard")
def dashboard():
    role = session.get("role")

    if role == "admin":
        return redirect("/admin")
    elif role == "pegawai":
        return redirect("/pegawai")
    elif role == "pengurus":
        return redirect("/pengurus")
    elif role == "user":
        return redirect("/booking")

    return redirect("/")

@app.route("/user")
def user():
    return redirect("/booking")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)