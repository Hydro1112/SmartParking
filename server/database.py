
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
            id TEXT PRIMARY KEY,                   -- ID vé: H001/N001/T001
            vehicle_id INTEGER NOT NULL,           -- FK → vehicles.id
            plate TEXT NOT NULL,                   -- Biển số xe
            ticket_type TEXT NOT NULL,             -- Loại vé (hour/day/month)
            checkin_time TEXT NOT NULL,            -- Thời gian vào
            checkout_time TEXT,                    -- Thời gian ra
            duration INTEGER,                      -- Thời gian gửi (phút/giờ)
            parking_spot TEXT,                     -- Vị trí đỗ
            status TEXT DEFAULT 'active',          -- Trạng thái vé
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
    parking_lots = [
        ("Bãi xe A", 100, "Cổng chính - Khu A", 20),
        ("Bãi xe B", 50, "Cổng sau - Khu B", 10),
        ("Bãi xe C", 30, "Tầng hầm - Khu C", 30),   # full
        ("Bãi xe D", 200, "Khu D - Gần sân vận động", 120),
        ("Bãi xe E", 150, "Khu E - Nhà điều hành", 75),
        ("Bãi xe F", 20, "Khu F - Sát tường rào", 5),
        ("Bãi xe G", 500, "Khu G - Ngoài trời", 450),
        ("Bãi xe H", 80, "Khu H - Tòa nhà văn phòng", 65),
        ("Bãi xe I", 60, "Khu I - Ký túc xá", 25),
        ("Bãi xe J", 40, "Khu J - Nhà xe công vụ", 10),
        ("Bãi xe K", 120, "Khu K - Trung tâm thương mại", 100),
        ("Bãi xe L", 15, "Khu L - VIP", 5),
    ]
    cursor.executemany("""
        INSERT INTO parking_lot (name, capacity, location, current_occupancy)
        VALUES (?, ?, ?, ?)
    """, parking_lots)

    # 2. Phương tiện
    vehicles = [
        ("V001", "30A-12345", "Nguyễn Văn A", "0905123456", "Ô tô", "RFID001", "images/30A-12345.jpg"),
        ("V002", "29B-67890", "Trần Thị B", "0905678901", "Xe máy", "RFID002", "images/29B-67890.jpg"),
        ("V003", "88C-24680", "Lê Văn C", "0905246802", "Ô tô", "RFID003", "images/88C-24680.jpg"),
        ("V004", "51D-11223", "Phạm Văn D", "0911223344", "Taxi", "RFID004", "images/51D-11223.jpg"),
        ("V005", "43F-44556", "Ngô Thị E", "0922334455", "Xe tải", "RFID005", "images/43F-44556.jpg"),
        ("V006", "79G-77889", "Hoàng Văn F", "0933445566", "Ô tô", "RFID006", "images/79G-77889.jpg"),
        ("V007", "12H-99001", "Phan Thị G", "0944556677", "Xe máy", "RFID007", "images/12H-99001.jpg"),
        ("V008", "30K-23456", "Đỗ Văn H", "0955667788", "Ô tô", "RFID008", "images/30K-23456.jpg"),
        ("V009", "29M-98765", "Vũ Thị I", "0966778899", "Xe đạp điện", "RFID009", "images/29M-98765.jpg"),
        ("V010", "88N-54321", "Nguyễn Văn J", "0977889900", "Ô tô", "RFID010", "images/88N-54321.jpg"),
        ("V011", "51P-11111", "Trần Văn K", "0988990011", "Xe máy", "RFID011", "images/51P-11111.jpg"),
        ("V012", "43Q-22222", "Nguyễn Thị L", "0999001122", "Ô tô", "RFID012", "images/43Q-22222.jpg"),
        ("V013", "79R-33333", "Lê Văn M", "0901112233", "Xe khách", "RFID013", "images/79R-33333.jpg"),
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
        ("H003", "V004", "51D-11223", "hourly", now - timedelta(minutes=45), None, None, "C2", "active"),
        ("H004", "V005", "43F-44556", "hourly", now - timedelta(hours=3), now - timedelta(hours=1), 120, "D1", "closed"),
        ("N002", "V006", "79G-77889", "daily", now - timedelta(days=1), None, None, "C5", "active"),
        ("T002", "V007", "12H-99001", "monthly", now - timedelta(days=20), None, None, "D3", "active"),
        ("H005", "V008", "30K-23456", "hourly", now - timedelta(minutes=30), None, None, "E1", "active"),
        ("N003", "V009", "29M-98765", "daily", now - timedelta(hours=10), now - timedelta(hours=1), 540, "E2", "closed"),
        ("T003", "V010", "88N-54321", "monthly", now - timedelta(days=40), now - timedelta(days=5), None, "F1", "expired"),
        ("H006", "V011", "51P-11111", "hourly", now - timedelta(hours=1), None, None, "G1", "active"),
        ("H007", "V012", "43Q-22222", "hourly", now - timedelta(hours=2), None, None, "H1", "active"),
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
        ("V004", "51D-11223", "Gate C", 3, "in", "H003", "history/51D-11223_in.jpg"),
        ("V005", "43F-44556", "Gate D", 4, "in", "H004", "history/43F-44556_in.jpg"),
        ("V006", "79G-77889", "Gate C", 3, "out", "N002", "history/79G-77889_out.jpg"),
        ("V007", "12H-99001", "Gate D", 4, "in", "T002", "history/12H-99001_in.jpg"),
        ("V008", "30K-23456", "Gate E", 5, "in", "H005", "history/30K-23456_in.jpg"),
        ("V009", "29M-98765", "Gate E", 5, "out", "N003", "history/29M-98765_out.jpg"),
        ("V010", "88N-54321", "Gate F", 6, "in", "T003", "history/88N-54321_in.jpg"),
        ("V011", "51P-11111", "Gate G", 7, "in", "H006", "history/51P-11111_in.jpg"),
        ("V012", "43Q-22222", "Gate H", 8, "in", "H007", "history/43Q-22222_in.jpg"),
    ]
    cursor.executemany("""
        INSERT INTO history (vehicle_id, plate, gate, camera_id, event_type, ticket_id, image_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, history)

    # 5. Thanh toán
    payments = [
        ("H002", 15000.0),
        ("H004", 25000.0),
        ("N003", 50000.0),
        ("T003", 1200000.0),
        ("H006", 10000.0),
        ("H007", 12000.0),
        ("H005", 8000.0),
        ("N002", 60000.0),
        ("H003", 7000.0),
        ("H001", 20000.0),
    ]
    cursor.executemany("""
        INSERT INTO payments (ticket_id, amount)
        VALUES (?, ?)
    """, payments)

    # 6. Camera
    cameras = [
        ("Gate A", "192.168.1.10", "active"),
        ("Gate B", "192.168.1.11", "inactive"),
        ("Gate C", "192.168.1.12", "active"),
        ("Gate D", "192.168.1.13", "active"),
        ("Gate E", "192.168.1.14", "inactive"),
        ("Gate F", "192.168.1.15", "active"),
        ("Gate G", "192.168.1.16", "active"),
        ("Gate H", "192.168.1.17", "inactive"),
        ("Gate I", "192.168.1.18", "active"),
        ("Gate J", "192.168.1.19", "active"),
    ]
    cursor.executemany("""
        INSERT INTO cameras (gate, ip_address, status)
        VALUES (?, ?, ?)
    """, cameras)

    # 7. Cảnh báo
    alerts = [
        ("overstay", "Xe 30A-12345 gửi quá thời gian 2h", "warning", 0),
        ("camera_error", "Camera Gate B mất tín hiệu", "critical", 0),
        ("unpaid", "Xe 29B-67890 rời bãi chưa thanh toán", "critical", 0),
        ("system_error", "Máy chủ xử lý vé gặp sự cố", "critical", 1),
        ("fire_alarm", "Phát hiện khói tại bãi xe C", "critical", 0),
        ("intrusion", "Xe không đăng ký đi vào Gate D", "warning", 0),
        ("rfid_error", "Thẻ RFID V005 không hợp lệ", "warning", 1),
        ("low_capacity", "Bãi xe G đã đạt 90% công suất", "info", 0),
        ("payment_delay", "Thanh toán H006 chậm 15 phút", "info", 1),
        ("expired_ticket", "Vé tháng T003 đã hết hạn", "warning", 0),
    ]
    cursor.executemany("""
        INSERT INTO alerts (alert_type, message, severity, resolved)
        VALUES (?, ?, ?, ?)
    """, alerts)

    conn.commit()
    conn.close()
    print("✅ Database initialized and seeded successfully!")


if __name__ == "__main__":
    init_db()
    seed_data()
