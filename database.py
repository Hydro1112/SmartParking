import sqlite3
from datetime import datetime

DB_PATH = "parking.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Danh sách xe đăng ký
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registered (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate TEXT UNIQUE NOT NULL
        )
    ''')

    # Lịch sử ra/vào (lưu cả car_id từ SORT)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_id INTEGER NOT NULL,
            plate TEXT NOT NULL,
            camera TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


def insert_plate_event(car_id: int, plate: str, camera: str):
    """Thêm sự kiện mới vào bảng history."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO history (car_id, plate, camera, timestamp)
        VALUES (?, ?, ?, ?)
        ''',
        (car_id, plate, camera, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()


def update_plate_event(car_id: int, new_plate: str):
    """Cập nhật lại biển số cho car_id (chỉ giữ 1 record duy nhất/xe)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        '''
        UPDATE history
        SET plate = ?
        WHERE car_id = ?
        ''',
        (new_plate, car_id)
    )
    conn.commit()
    conn.close()


def get_registered_plates():
    """Lấy danh sách biển số đã đăng ký (trả về set)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT plate FROM registered")
    rows = [r[0] for r in cursor.fetchall()]
    conn.close()
    return set(rows)


def register_plate(plate: str):
    """Đăng ký biển số mới (nếu chưa có)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO registered (plate) VALUES (?)", (plate,)
    )
    conn.commit()
    conn.close()


def get_all_history():
    """Lấy toàn bộ lịch sử ra/vào (mới nhất trước)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT car_id, plate, camera, timestamp FROM history ORDER BY timestamp DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows
