import pymysql

HOST = 'localhost'
USER = 'root'
PASSWORD = ''
DB = 'booking_lapangan'


def get_db():
    return pymysql.connect(
        host=HOST,
        user=USER,
        password=PASSWORD,
        database=DB,
        cursorclass=pymysql.cursors.DictCursor,
    )


def main():
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS lapangan (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nama_lapangan VARCHAR(255) NOT NULL UNIQUE,
                deskripsi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS bookings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nama_pemesan VARCHAR(255) NOT NULL,
                nama_lapangan VARCHAR(255) NOT NULL,
                tanggal DATE NOT NULL,
                jam_mulai TIME NOT NULL,
                jam_selesai TIME NOT NULL,
                catatan TEXT,
                role_pemesan VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        # Users table for authentication
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
        print("Tabel lapangan dan bookings telah dibuat atau sudah ada.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
    # Attempt to migrate existing JSON users into DB (if any)
    try:
        from user_utils import migrate_json_users
        migrate_json_users()
        print("Migrasi users.json ke tabel users selesai (jika ada).")
    except Exception as e:
        print("Migrasi users gagal:", e)
