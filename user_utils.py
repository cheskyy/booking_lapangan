import os
import json
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql
from config import Config

BASE_DIR = os.path.dirname(__file__)
USERS_FILE = os.path.join(BASE_DIR, "users.json")


def get_db():
    return pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_user(username):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT username, password, role FROM users WHERE username = %s", (username,))
        return cur.fetchone()
    finally:
        conn.close()


def create_user(username, password, role="user"):
    hashed = generate_password_hash(password)
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, hashed, role))
        conn.commit()
    finally:
        conn.close()


def update_user(username, password=None, role=None):
    conn = get_db()
    try:
        cur = conn.cursor()
        if password and role:
            hashed = generate_password_hash(password)
            cur.execute("UPDATE users SET password=%s, role=%s WHERE username=%s", (hashed, role, username))
        elif password:
            hashed = generate_password_hash(password)
            cur.execute("UPDATE users SET password=%s WHERE username=%s", (hashed, username))
        elif role:
            cur.execute("UPDATE users SET role=%s WHERE username=%s", (role, username))
        else:
            return
        conn.commit()
    finally:
        conn.close()


def delete_user(username):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE username = %s", (username,))
        conn.commit()
    finally:
        conn.close()


def list_users():
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT username, role, created_at FROM users ORDER BY created_at DESC")
        return cur.fetchall()
    finally:
        conn.close()


def verify_password(stored_hash, password):
    return check_password_hash(stored_hash, password)


def ensure_users_table():
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        conn.commit()
    finally:
        conn.close()


def migrate_json_users():
    # Ensure the users table exists before attempting migration.
    ensure_users_table()

    if not os.path.exists(USERS_FILE):
        return
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return

    conn = get_db()
    try:
        cur = conn.cursor()
        for username, info in data.items():
            # skip if exists
            cur.execute("SELECT username FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                continue
            pwd = info.get('password', '')
            role = info.get('role', 'user')
            hashed = generate_password_hash(pwd)
            cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, hashed, role))
        conn.commit()
    finally:
        conn.close()
