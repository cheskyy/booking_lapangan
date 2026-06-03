import json
import os
import jwt
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, request, jsonify, session
from flask_cors import CORS
import pymysql

from config import Config

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

BASE_DIR = os.path.dirname(__file__)
USERS_FILE = os.path.join(BASE_DIR, "users.json")


def get_db():
    """Create database connection"""
    return pymysql.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        password=app.config['MYSQL_PASSWORD'],
        database=app.config['MYSQL_DB'],
        cursorclass=pymysql.cursors.DictCursor
    )


def load_users():
    """Load users from JSON file"""
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "admin": {"password": "123", "role": "admin"},
        "pegawai": {"password": "123", "role": "pegawai"},
        "pengurus": {"password": "123", "role": "pengurus"},
    }


def save_users(users_data):
    """Save users to JSON file"""
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users_data, f, indent=2, ensure_ascii=False)


def create_token(username, role):
    """Create JWT token"""
    payload = {
        'username': username,
        'role': role,
        'exp': datetime.utcnow() + timedelta(seconds=app.config['JWT_EXPIRY']),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, app.config['JWT_SECRET'], algorithm=app.config['JWT_ALGORITHM'])
    return token


def verify_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, app.config['JWT_SECRET'], algorithms=[app.config['JWT_ALGORITHM']])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(allowed_roles=None):
    """Decorator for token verification"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get('Authorization', '')
            
            if not auth_header:
                return jsonify({'success': False, 'message': 'Token tidak ditemukan'}), 401
            
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'success': False, 'message': 'Format Authorization header salah'}), 401
            
            payload = verify_token(token)
            if not payload:
                return jsonify({'success': False, 'message': 'Token tidak valid atau expired'}), 401
            
            # Check role
            if allowed_roles and payload.get('role') not in allowed_roles + ['admin']:
                return jsonify({'success': False, 'message': 'Akses ditolak: role tidak sesuai'}), 403
            
            request.user = payload
            return f(*args, **kwargs)
        
        return wrapper
    return decorator


users = load_users()

# ── AUTH ENDPOINTS ─────────────────────────────────

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login dan dapatkan JWT token"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'success': False, 'message': 'Username dan password diperlukan'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    user = users.get(username)
    if not user or user['password'] != password:
        return jsonify({'success': False, 'message': 'Username atau password salah'}), 401
    
    token = create_token(username, user['role'])
    return jsonify({
        'success': True,
        'message': 'Login berhasil',
        'data': {
            'token': token,
            'username': username,
            'role': user['role']
        }
    }), 200


@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register user baru"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'success': False, 'message': 'Username dan password diperlukan'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if username in users:
        return jsonify({'success': False, 'message': 'Username sudah terdaftar'}), 409
    
    users[username] = {'password': password, 'role': 'user'}
    save_users(users)
    
    return jsonify({
        'success': True,
        'message': 'Registrasi berhasil'
    }), 201


@app.route('/api/auth/verify', methods=['GET'])
@token_required()
def verify():
    """Verify token validity"""
    return jsonify({
        'success': True,
        'message': 'Token valid',
        'data': request.user
    }), 200


# ── LAPANGAN ENDPOINTS ─────────────────────────────

@app.route('/api/lapangan', methods=['GET'])
@token_required()
def get_lapangan():
    """Get semua lapangan"""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, nama_lapangan, deskripsi, created_at FROM lapangan ORDER BY nama_lapangan")
        lapangans = cur.fetchall()
    finally:
        conn.close()
    
    return jsonify({
        'success': True,
        'data': lapangans
    }), 200


@app.route('/api/lapangan', methods=['POST'])
@token_required(allowed_roles=['admin'])
def create_lapangan():
    """Create lapangan baru (admin only)"""
    data = request.get_json()
    
    if not data or not data.get('nama_lapangan'):
        return jsonify({'success': False, 'message': 'Nama lapangan diperlukan'}), 400
    
    nama = data.get('nama_lapangan', '').strip()
    deskripsi = data.get('deskripsi', '').strip()
    
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO lapangan (nama_lapangan, deskripsi) VALUES (%s, %s)",
            (nama, deskripsi)
        )
        conn.commit()
        lapangan_id = cur.lastrowid
    finally:
        conn.close()
    
    return jsonify({
        'success': True,
        'message': 'Lapangan berhasil ditambahkan',
        'data': {'id': lapangan_id, 'nama_lapangan': nama}
    }), 201


@app.route('/api/lapangan/<int:id>', methods=['DELETE'])
@token_required(allowed_roles=['admin'])
def delete_lapangan(id):
    """Delete lapangan (admin only)"""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM lapangan WHERE id = %s", (id,))
        conn.commit()
        
        if cur.rowcount == 0:
            return jsonify({'success': False, 'message': 'Lapangan tidak ditemukan'}), 404
    finally:
        conn.close()
    
    return jsonify({
        'success': True,
        'message': 'Lapangan berhasil dihapus'
    }), 200


# ── BOOKING ENDPOINTS ──────────────────────────────

@app.route('/api/booking', methods=['GET'])
@token_required()
def get_bookings():
    """Get bookings berdasarkan role"""
    conn = get_db()
    try:
        cur = conn.cursor()
        
        if request.user['role'] == 'user':
            cur.execute("""
                SELECT id, nama_pemesan, nama_lapangan, tanggal, jam_mulai, jam_selesai, 
                       catatan, role_pemesan, status, created_at 
                FROM bookings 
                WHERE nama_pemesan = %s 
                ORDER BY created_at DESC
            """, (request.user['username'],))
        else:
            cur.execute("""
                SELECT id, nama_pemesan, nama_lapangan, tanggal, jam_mulai, jam_selesai, 
                       catatan, role_pemesan, status, created_at 
                FROM bookings 
                ORDER BY created_at DESC
            """)
        
        bookings = cur.fetchall()
    finally:
        conn.close()
    
    return jsonify({
        'success': True,
        'data': bookings
    }), 200


@app.route('/api/booking', methods=['POST'])
@token_required()
def create_booking():
    """Create booking baru"""
    data = request.get_json()
    
    required_fields = ['nama_lapangan', 'tanggal', 'jam_mulai', 'jam_selesai']
    if not data or not all(field in data for field in required_fields):
        return jsonify({'success': False, 'message': 'Field tidak lengkap'}), 400
    
    nama_lapangan = data.get('nama_lapangan', '').strip()
    tanggal = data.get('tanggal', '')
    jam_mulai = data.get('jam_mulai', '')
    jam_selesai = data.get('jam_selesai', '')
    catatan = data.get('catatan', '').strip()
    
    # Validasi jam
    if jam_mulai >= jam_selesai:
        return jsonify({'success': False, 'message': 'Jam mulai harus lebih awal dari jam selesai'}), 400
    
    conn = get_db()
    try:
        cur = conn.cursor()
        
        # Check konflik jadwal
        cur.execute("""
            SELECT COUNT(*) AS count FROM bookings 
            WHERE nama_lapangan = %s AND tanggal = %s 
            AND status IN ('Menunggu Persetujuan', 'Disetujui (ACC)') 
            AND jam_mulai < %s AND jam_selesai > %s
        """, (nama_lapangan, tanggal, jam_selesai, jam_mulai))
        
        conflict = cur.fetchone().get('count', 0)
        if conflict:
            return jsonify({'success': False, 'message': 'Lapangan sudah tidak tersedia pada jadwal tersebut'}), 409
        
        # Insert booking
        cur.execute("""
            INSERT INTO bookings 
            (nama_pemesan, nama_lapangan, tanggal, jam_mulai, jam_selesai, catatan, role_pemesan, status) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (request.user['username'], nama_lapangan, tanggal, jam_mulai, jam_selesai, catatan, request.user['role'], 'Menunggu Persetujuan'))
        
        conn.commit()
        booking_id = cur.lastrowid
    finally:
        conn.close()
    
    return jsonify({
        'success': True,
        'message': 'Booking berhasil disimpan dan menunggu persetujuan',
        'data': {'id': booking_id}
    }), 201


@app.route('/api/booking/<int:id>', methods=['GET'])
@token_required()
def get_booking_detail(id):
    """Get detail booking"""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nama_pemesan, nama_lapangan, tanggal, jam_mulai, jam_selesai, 
                   catatan, role_pemesan, status, created_at 
            FROM bookings WHERE id = %s
        """, (id,))
        
        booking = cur.fetchone()
    finally:
        conn.close()
    
    if not booking:
        return jsonify({'success': False, 'message': 'Booking tidak ditemukan'}), 404
    
    return jsonify({
        'success': True,
        'data': booking
    }), 200


@app.route('/api/booking/<int:id>/status', methods=['PUT'])
@token_required(allowed_roles=['admin', 'pengurus'])
def update_booking_status(id):
    """Update status booking"""
    data = request.get_json()
    
    if not data or not data.get('action'):
        return jsonify({'success': False, 'message': 'Action diperlukan'}), 400
    
    status_map = {
        'acc': 'Disetujui (ACC)',
        'ditolak': 'Ditolak',
        'selesai': 'Selesai',
        'batal': 'Dibatalkan',
    }
    
    action = data.get('action', '').lower()
    new_status = status_map.get(action)
    
    if not new_status:
        return jsonify({'success': False, 'message': 'Action tidak dikenal'}), 400
    
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE bookings SET status = %s WHERE id = %s", (new_status, id))
        conn.commit()
        
        if cur.rowcount == 0:
            return jsonify({'success': False, 'message': 'Booking tidak ditemukan'}), 404
    finally:
        conn.close()
    
    return jsonify({
        'success': True,
        'message': f'Status berhasil diubah menjadi {new_status}'
    }), 200


@app.route('/api/booking/<int:id>/cancel', methods=['POST'])
@token_required()
def cancel_booking(id):
    """Cancel booking"""
    conn = get_db()
    try:
        cur = conn.cursor()
        
        # Check ownership if user role
        if request.user['role'] == 'user':
            cur.execute("SELECT nama_pemesan FROM bookings WHERE id = %s", (id,))
            booking = cur.fetchone()
            
            if not booking or booking['nama_pemesan'] != request.user['username']:
                return jsonify({'success': False, 'message': 'Akses ditolak'}), 403
        
        cur.execute("UPDATE bookings SET status = %s WHERE id = %s", ('Dibatalkan', id))
        conn.commit()
        
        if cur.rowcount == 0:
            return jsonify({'success': False, 'message': 'Booking tidak ditemukan'}), 404
    finally:
        conn.close()
    
    return jsonify({
        'success': True,
        'message': 'Booking dibatalkan'
    }), 200


@app.route('/api/booking/<int:id>', methods=['DELETE'])
@token_required(allowed_roles=['admin'])
def delete_booking(id):
    """Delete booking (admin only)"""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM bookings WHERE id = %s", (id,))
        conn.commit()
        
        if cur.rowcount == 0:
            return jsonify({'success': False, 'message': 'Booking tidak ditemukan'}), 404
    finally:
        conn.close()
    
    return jsonify({
        'success': True,
        'message': 'Booking berhasil dihapus'
    }), 200


# ── JADWAL ENDPOINTS ───────────────────────────────

@app.route('/api/jadwal', methods=['GET'])
@token_required()
def get_jadwal():
    """Get jadwal lapangan per tanggal"""
    tanggal = request.args.get('tanggal')
    
    if not tanggal:
        return jsonify({'success': False, 'message': 'Parameter tanggal diperlukan'}), 400
    
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM lapangan ORDER BY nama_lapangan")
        lapangans = cur.fetchall()
        
        cur.execute("""
            SELECT * FROM bookings 
            WHERE tanggal = %s 
            ORDER BY nama_lapangan, jam_mulai
        """, (tanggal,))
        bookings = cur.fetchall()
    finally:
        conn.close()
    
    field_schedule = []
    for lap in lapangans:
        field_bookings = [b for b in bookings if b['nama_lapangan'] == lap['nama_lapangan']]
        
        if not field_bookings:
            status = 'Tersedia'
        else:
            active = any(b['status'] in ['Menunggu Persetujuan', 'Disetujui (ACC)'] for b in field_bookings)
            status = 'Terisi' if active else 'Tersedia'
        
        field_schedule.append({
            'lapangan': lap,
            'status': status,
            'bookings': field_bookings,
        })
    
    return jsonify({
        'success': True,
        'data': {
            'tanggal': tanggal,
            'lapangan': field_schedule
        }
    }), 200


# ── ADMIN ENDPOINTS ────────────────────────────────

@app.route('/api/admin/users', methods=['GET'])
@token_required(allowed_roles=['admin'])
def admin_get_users():
    """Get semua users"""
    return jsonify({
        'success': True,
        'data': list(users.items())
    }), 200


@app.route('/api/admin/users', methods=['POST'])
@token_required(allowed_roles=['admin'])
def admin_create_user():
    """Create user baru"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password') or not data.get('role'):
        return jsonify({'success': False, 'message': 'Username, password, dan role diperlukan'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'user')
    
    if username in users:
        return jsonify({'success': False, 'message': 'Username sudah ada'}), 409
    
    users[username] = {'password': password, 'role': role}
    save_users(users)
    
    return jsonify({
        'success': True,
        'message': f'User {username} berhasil dibuat'
    }), 201


@app.route('/api/admin/users/<username>', methods=['DELETE'])
@token_required(allowed_roles=['admin'])
def admin_delete_user(username):
    """Delete user"""
    if username == request.user['username']:
        return jsonify({'success': False, 'message': 'Tidak bisa menghapus akun sendiri'}), 400
    
    if username not in users:
        return jsonify({'success': False, 'message': 'User tidak ditemukan'}), 404
    
    users.pop(username)
    save_users(users)
    
    return jsonify({
        'success': True,
        'message': f'User {username} berhasil dihapus'
    }), 200


@app.route('/api/admin/laporan', methods=['GET'])
@token_required(allowed_roles=['admin'])
def admin_laporan():
    """Get laporan statistik"""
    conn = get_db()
    try:
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) AS total FROM bookings")
        total_booking = cur.fetchone().get('total', 0)
        
        cur.execute("SELECT role_pemesan, COUNT(*) AS total FROM bookings GROUP BY role_pemesan")
        total_per_role = cur.fetchall()
        
        cur.execute("SELECT nama_lapangan, COUNT(*) AS total FROM bookings GROUP BY nama_lapangan")
        total_per_lapangan = cur.fetchall()
        
        cur.execute("SELECT tanggal, COUNT(*) AS total FROM bookings GROUP BY tanggal ORDER BY tanggal DESC LIMIT 10")
        total_per_tanggal = cur.fetchall()
    finally:
        conn.close()
    
    return jsonify({
        'success': True,
        'data': {
            'total_booking': total_booking,
            'per_role': total_per_role,
            'per_lapangan': total_per_lapangan,
            'per_tanggal': total_per_tanggal,
        }
    }), 200


# ── ERROR HANDLERS ─────────────────────────────────

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Endpoint tidak ditemukan'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': 'Internal server error'}), 500


# ── HEALTH CHECK ───────────────────────────────────

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'message': 'API berjalan normal',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=port)
