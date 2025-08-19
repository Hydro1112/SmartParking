# database.py
import sqlite3
from datetime import datetime
from pathlib import Path

# Đường dẫn DB cố định nằm cùng thư mục
DB_PATH = Path(__file__).parent / "parking.db"


def get_connection():
    """Tạo connection tới DB."""
    return sqlite3.connect(DB_PATH)


def init_db():
    """Khởi tạo các bảng nếu chưa tồn tại."""
    conn = get_connection()
    cursor = conn.cursor()

    # Bảng biển số đăng ký
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registered (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate TEXT UNIQUE NOT NULL
        )
    ''')

    # Bảng lịch sử vào/ra
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            car_id INTEGER NOT NULL,
            plate TEXT NOT NULL,
            camera TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')

    # Bảng vé xe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id TEXT PRIMARY KEY,
            plate TEXT,
            vehicle_type TEXT,   -- motor/car
            ticket_type TEXT,    -- hourly/overnight/monthly
            entry_time TEXT,     -- ISO
            exit_time  TEXT,     -- ISO or NULL
            amount REAL DEFAULT 0,
            status TEXT          -- active/closed/cancelled
        )
    ''')

    conn.commit()
    conn.close()


# ========================
# Các hàm thao tác dữ liệu
# ========================

def insert_plate_event(car_id: int, plate: str, camera: str):
    """Thêm sự kiện mới vào bảng history."""
    conn = get_connection()
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
    """Cập nhật biển số cho car_id trong history."""
    conn = get_connection()
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
    """Lấy danh sách biển số đã đăng ký (set)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT plate FROM registered")
    rows = [r[0] for r in cursor.fetchall()]
    conn.close()
    return set(rows)


def register_plate(plate: str):
    """Đăng ký biển số mới (nếu chưa có)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO registered (plate) VALUES (?)", (plate,)
    )
    conn.commit()
    conn.close()


def get_all_history():
    """Lấy toàn bộ lịch sử ra/vào (mới nhất trước)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT car_id, plate, camera, timestamp FROM history ORDER BY timestamp DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows
