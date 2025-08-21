
import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path


DB_PATH = Path(__file__).parent / "parking.db"


def get_connection():
   
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # BẢNG 1: Thông tin bãi xe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parking_lot (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            location TEXT,
            current_occupancy INTEGER DEFAULT 0
        )
    """)

    # BẢNG 2: Phương tiện
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id TEXT PRIMARY KEY,
            plate TEXT UNIQUE NOT NULL,
            owner_name TEXT,
            owner_phone TEXT,
            vehicle_type TEXT NOT NULL,
            rfid_tag TEXT NOT NULL,
            license_plate_image TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # BẢNG 3: Vé xe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id TEXT PRIMARY KEY,
            vehicle_id TEXT NOT NULL,
            plate TEXT NOT NULL,
            ticket_type TEXT NOT NULL,
            checkin_time TEXT NOT NULL,
            checkout_time TEXT,
            duration INTEGER,
            parking_spot TEXT,
            status TEXT DEFAULT 'active',
            FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
        )
    """)

    # BẢNG 4: Lịch sử ra/vào
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id TEXT NOT NULL,
            plate TEXT NOT NULL,
            gate TEXT NOT NULL,
            camera_id INTEGER,
            event_type TEXT NOT NULL,
            ticket_id TEXT,
            image_url TEXT,
            FOREIGN KEY(vehicle_id) REFERENCES vehicles(id),
            FOREIGN KEY(ticket_id) REFERENCES tickets(id),
            FOREIGN KEY(camera_id) REFERENCES cameras(id)
        )
    """)

    # BẢNG 5: Thanh toán
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY(ticket_id) REFERENCES tickets(id)
        )
    """)

    # BẢNG 6: Camera
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cameras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gate TEXT NOT NULL,
            ip_address TEXT,
            status TEXT DEFAULT 'active'
        )
    """)

    # BẢNG 7: Cảnh báo
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT DEFAULT 'info',
            resolved INTEGER DEFAULT 0
        )
    """)

    conn.commit()   # ✅ QUAN TRỌNG: lưu lại schema
    conn.close()


def seed_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Bãi xe
    cursor.executemany("""
        INSERT INTO parking_lot (name, capacity, location, current_occupancy)
        VALUES (?, ?, ?, ?)
    """, [
        ("Bãi xe A", 100, "Cổng chính - Khu A", 20),
        ("Bãi xe B", 50, "Cổng sau - Khu B", 10)
    ])

    # 2. Phương tiện
    vehicles = [
        ("V001", "30A-12345", "Nguyễn Văn A", "0905123456", "Ô tô", "RFID001", "images/30A-12345.jpg"),
        ("V002", "29B-67890", "Trần Thị B", "0905678901", "Xe máy", "RFID002", "images/29B-67890.jpg"),
        ("V003", "88C-24680", "Lê Văn C", "0905246802", "Ô tô", "RFID003", "images/88C-24680.jpg")
    ]
    cursor.executemany("""
        INSERT INTO vehicles (id, plate, owner_name, owner_phone, vehicle_type, rfid_tag, license_plate_image)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, vehicles)

    # 3. Vé
    now = datetime.now()
    tickets = [
        ("H001", "V001", "30A-12345", "hourly", now - timedelta(hours=2), None, None, "A1", "active"),
        ("H002", "V002", "29B-67890", "hourly", now - timedelta(hours=1, minutes=30), now - timedelta(minutes=10), 90, "B5", "closed"),
        ("N001", "V003", "88C-24680", "daily", now - timedelta(hours=5), None, None, "A3", "active"),
        ("T001", "V001", "30A-12345", "monthly", now - timedelta(days=10), None, None, "A2", "active"),
    ]
    cursor.executemany("""
        INSERT INTO tickets (id, vehicle_id, plate, ticket_type, checkin_time, checkout_time, duration, parking_spot, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, tickets)

    # 4. Lịch sử
    history = [
        ("V001", "30A-12345", "Gate A", 1, "in", "H001", "history/30A-12345_in.jpg"),
        ("V001", "30A-12345", "Gate A", 1, "out", "H001", "history/30A-12345_out.jpg"),
        ("V002", "29B-67890", "Gate B", 2, "in", "H002", "history/29B-67890_in.jpg"),
        ("V003", "88C-24680", "Gate A", 1, "in", "N001", "history/88C-24680_in.jpg"),
    ]
    cursor.executemany("""
        INSERT INTO history (vehicle_id, plate, gate, camera_id, event_type, ticket_id, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, history)

    # 5. Thanh toán
    payments = [("H002", 15000.0)]
    cursor.executemany("""
        INSERT INTO payments (ticket_id, amount)
        VALUES (?, ?)
    """, payments)

    # 6. Camera
    cursor.executemany("""
        INSERT INTO cameras (gate, ip_address, status)
        VALUES (?, ?, ?)
    """, [
        ("Gate A", "192.168.1.10", "active"),
        ("Gate B", "192.168.1.11", "inactive")
    ])

    # 7. Cảnh báo
    cursor.executemany("""
        INSERT INTO alerts (alert_type, message, severity, resolved)
        VALUES (?, ?, ?, ?)
    """, [
        ("overstay", "Xe 30A-12345 gửi quá thời gian 2h", "warning", 0),
        ("camera_error", "Camera Gate B mất tín hiệu", "critical", 0)
    ])

    conn.commit()
    conn.close()
    print("✅ Database initialized and seeded successfully!")


if __name__ == "__main__":
    init_db()
    seed_data()
