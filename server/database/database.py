
import sqlite3
import random
from datetime import datetime, timedelta
from pathlib import Path
import uuid
DB_PATH = Path(__file__).resolve().parent / "parking.db"

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
            timestamp TEXT NOT NULL,
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
    init_db() # Luôn khởi tạo lại DB trống trước khi seed
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.now()

    # 1. Bãi xe - Cập nhật số xe active ở cuối
    cursor.execute("INSERT INTO parking_lot VALUES (1, 'Bãi xe trung tâm', 500, 'Khu A', 0)")

    # 2. Phương tiện (Thêm nhiều xe hơn)
    vehicles = [
        ("V001", "30A-12345", "Nguyễn Văn A", "0901112221", "car", "images/30A-12345.jpg"),
        ("V002", "29B-67890", "Trần Thị B", "0902223332", "motorbike", "images/29B-67890.jpg"),
        ("V003", "88C-24680", "Lê Văn C", "0903334443", "car", "images/88C-24680.jpg"),
        ("V004", "51D-11223", "Phạm Thị D", "0904445554", "car", "images/51D-11223.jpg"),
        ("V005", "43F-44556", "Vũ Văn E", "0905556665", "motorbike", "images/43F-44556.jpg"),
        ("V006", "79G-77889", "Hoàng Văn F", "0906667776", "car", "images/79G-77889.jpg"),
        ("V007", "99H-12345", "Đặng Thị G", "0907778887", "motorbike", "images/99H-12345.jpg"),
        ("V008", "30K-54321", "Bùi Văn H", "0908889998", "car", "images/30K-54321.jpg"),
        ("V009", "59L-98765", "Hồ Thị I", "0909990009", "motorbike", "images/59L-98765.jpg"),
        ("V010", "43M-11111", "Dương Văn K", "0911112221", "car", "images/43M-11111.jpg"),
    ]
    cursor.executemany("INSERT INTO vehicles (id, plate, owner_name, owner_phone, vehicle_type, license_plate_image) VALUES (?, ?, ?, ?, ?, ?)", vehicles)

    # 3. Vé xe (Dữ liệu đa dạng cho 7 ngày gần nhất)
    tickets = [
        # --- NGÀY HÔM NAY ---
        ("H001", "V001", "30A-12345", "hourly", (now - timedelta(hours=2)).isoformat(), None, None, "A1", "active"), # Active
        ("H002", "V002", "29B-67890", "hourly", (now - timedelta(hours=8)).isoformat(), (now - timedelta(hours=1)).isoformat(), 420, "B1", "closed"),

        # --- Dữ liệu cho ngày hôm qua (1 day ago) ---
        ("H003", "V003", "88C-24680", "hourly", (now - timedelta(days=1, hours=5)).isoformat(), (now - timedelta(days=1, hours=2)).isoformat(), 180, "C1", "closed"),
        ("H004", "V004", "51D-11223", "hourly", (now - timedelta(days=1, hours=10)).isoformat(), None, None, "D1", "active"), # Active qua đêm

        # --- Dữ liệu cho 2 ngày trước ---
        ("H005", "V005", "43F-44556", "hourly", (now - timedelta(days=2, hours=12)).isoformat(), (now - timedelta(days=1, hours=8)).isoformat(), 1680, "E1", "closed"), # Gửi qua đêm
        ("H006", "V006", "79G-77889", "hourly", (now - timedelta(days=2, hours=4)).isoformat(), (now - timedelta(days=2, hours=1)).isoformat(), 180, "F1", "closed"),

        # --- Dữ liệu cho 3 ngày trước ---
        ("H007", "V007", "99H-12345", "hourly", (now - timedelta(days=3, hours=9)).isoformat(), (now - timedelta(days=3, hours=7)).isoformat(), 120, "G1", "closed"),
        ("H008", "V008", "30K-54321", "hourly", (now - timedelta(days=3, hours=20)).isoformat(), (now - timedelta(days=2, hours=6)).isoformat(), 600, "H1", "closed"), # Gửi qua đêm
        
        # --- Dữ liệu cho 4, 5, 6 ngày trước ---
        ("H009", "V009", "59L-98765", "hourly", (now - timedelta(days=4, hours=8)).isoformat(), (now - timedelta(days=4, hours=4)).isoformat(), 240, "I1", "closed"),
        ("H010", "V010", "43M-11111", "hourly", (now - timedelta(days=5, hours=18)).isoformat(), (now - timedelta(days=5, hours=10)).isoformat(), 480, "J1", "closed"),
        ("H011", "V001", "30A-12345", "hourly", (now - timedelta(days=6, hours=7)).isoformat(), (now - timedelta(days=6, hours=6)).isoformat(), 60, "K1", "closed"),
        
        # --- Vé tháng ---
        ("T001", "V006", "79G-77889", "monthly", (now - timedelta(days=15)).isoformat(), None, None, "M1", "active"), # Active
    ]
    cursor.executemany("INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", tickets)

    # 4. Lịch sử ra/vào (Tương ứng với các vé)
    history = [
        # Hôm nay
        ("V001", "30A-12345", "Gate A", 1, "in", "H001", (now - timedelta(hours=2)).isoformat()),
        ("V002", "29B-67890", "Gate A", 1, "in", "H002", (now - timedelta(hours=8)).isoformat()),
        ("V002", "29B-67890", "Gate B", 2, "out", "H002", (now - timedelta(hours=1)).isoformat()),
        # Hôm qua
        ("V003", "88C-24680", "Gate A", 1, "in", "H003", (now - timedelta(days=1, hours=5)).isoformat()),
        ("V003", "88C-24680", "Gate B", 2, "out", "H003", (now - timedelta(days=1, hours=2)).isoformat()),
        ("V004", "51D-11223", "Gate A", 1, "in", "H004", (now - timedelta(days=1, hours=10)).isoformat()),
        # 2 ngày trước
        ("V005", "43F-44556", "Gate A", 1, "in", "H005", (now - timedelta(days=2, hours=12)).isoformat()),
        ("V005", "43F-44556", "Gate B", 2, "out", "H005", (now - timedelta(days=1, hours=8)).isoformat()),
        ("V006", "79G-77889", "Gate A", 1, "in", "H006", (now - timedelta(days=2, hours=4)).isoformat()),
        ("V006", "79G-77889", "Gate B", 2, "out", "H006", (now - timedelta(days=2, hours=1)).isoformat()),
        # 3 ngày trước
        ("V007", "99H-12345", "Gate A", 1, "in", "H007", (now - timedelta(days=3, hours=9)).isoformat()),
        ("V007", "99H-12345", "Gate B", 2, "out", "H007", (now - timedelta(days=3, hours=7)).isoformat()),
        ("V008", "30K-54321", "Gate A", 1, "in", "H008", (now - timedelta(days=3, hours=20)).isoformat()),
        ("V008", "30K-54321", "Gate B", 2, "out", "H008", (now - timedelta(days=2, hours=6)).isoformat()),
        # 4, 5, 6 ngày trước
        ("V009", "59L-98765", "Gate A", 1, "in", "H009", (now - timedelta(days=4, hours=8)).isoformat()),
        ("V009", "59L-98765", "Gate B", 2, "out", "H009", (now - timedelta(days=4, hours=4)).isoformat()),
        ("V010", "43M-11111", "Gate A", 1, "in", "H010", (now - timedelta(days=5, hours=18)).isoformat()),
        ("V010", "43M-11111", "Gate B", 2, "out", "H010", (now - timedelta(days=5, hours=10)).isoformat()),
        ("V001", "30A-12345", "Gate A", 1, "in", "H011", (now - timedelta(days=6, hours=7)).isoformat()),
        ("V001", "30A-12345", "Gate B", 2, "out", "H011", (now - timedelta(days=6, hours=6)).isoformat()),
        # Lịch sử cho xe vé tháng
        ("V006", "79G-77889", "Gate A", 1, "in", "T001", (now - timedelta(days=15)).isoformat()),
        ("V006", "79G-77889", "Gate B", 2, "out", "T001", (now - timedelta(days=12)).isoformat()),
        ("V006", "79G-77889", "Gate A", 1, "in", "T001", (now - timedelta(days=5)).isoformat()),
        ("V006", "79G-77889", "Gate B", 2, "out", "T001", (now - timedelta(days=3)).isoformat()),
    ]
    cursor.executemany("INSERT INTO history (vehicle_id, plate, gate, camera_id, event_type, ticket_id, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)", history)

    # 5. Thanh toán
    payments = [
        ("T001", 60000.0), # Vé tháng
        ("H002", 3000.0),  # Trong ngày
        ("H003", 3000.0),  # Trong ngày
        ("H005", 10000.0), # Qua đêm
        ("H006", 3000.0),  # Trong ngày
        ("H007", 3000.0),  # Trong ngày
        ("H008", 10000.0), # Qua đêm
        ("H009", 3000.0),  # Trong ngày
        ("H010", 3000.0),  # Trong ngày
        ("H011", 3000.0),  # Trong ngày
    ]
    cursor.executemany("INSERT INTO payments (ticket_id, amount) VALUES (?, ?)", payments)

    # 6. Camera và Cảnh báo
    cursor.execute("INSERT INTO cameras VALUES (1, 'Cổng vào A', '192.168.1.10', 'active')")
    cursor.execute("INSERT INTO cameras VALUES (2, 'Cổng ra B', '192.168.1.11', 'active')")
    cursor.execute("INSERT INTO alerts VALUES (1, 'camera_error', 'Camera Cổng C mất tín hiệu', 'critical', 0)")
    cursor.execute("INSERT INTO alerts VALUES (2, 'full_capacity', 'Bãi xe gần đầy (95%)', 'warning', 0)")

    # 7. Cập nhật số xe đang trong bãi
    active_count = sum(1 for t in tickets if t[-1] == 'active')
    cursor.execute("UPDATE parking_lot SET current_occupancy = ? WHERE id = 1", (active_count,))
    
    conn.commit()
    conn.close()
    print(f"✅ Database đã được điền dữ liệu MỞ RỘNG ({len(tickets)} vé, {len(history)} sự kiện).")


if __name__ == "__main__":
    seed_data()