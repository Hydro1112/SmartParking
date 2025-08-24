import sqlite3
import datetime
from pathlib import Path
from typing import List, Optional, Any

# --- ĐỊNH NGHĨA CÁC LỚP MODEL DỮ LIỆU ---
# Các lớp này đại diện cho cấu trúc của mỗi bảng trong database.

class ParkingLot:
    """Đại diện cho một bãi xe trong bảng `parking_lot`."""
    def __init__(self, name: str, capacity: int, location: Optional[str] = None, current_occupancy: int = 0, id: Optional[int] = None):
        self.id = id
        self.name = name
        self.capacity = capacity
        self.location = location
        self.current_occupancy = current_occupancy

class Vehicle:
    """Đại diện cho một phương tiện trong bảng `vehicles`."""
    def __init__(self, id: str, plate: str, vehicle_type: str, license_plate_image: str, owner_name: Optional[str] = None, owner_phone: Optional[str] = None, created_at: Optional[str] = None):
        self.id = id
        self.plate = plate
        self.owner_name = owner_name
        self.owner_phone = owner_phone
        self.vehicle_type = vehicle_type
        self.license_plate_image = license_plate_image
        self.created_at = created_at or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class Ticket:
    """Đại diện cho một vé xe trong bảng `tickets`."""
    def __init__(self, id: str, vehicle_id: str, plate: str, ticket_type: str, checkin_time: str, status: str = 'active', checkout_time: Optional[str] = None, duration: Optional[int] = None, parking_spot: Optional[str] = None):
        self.id = id
        self.vehicle_id = vehicle_id
        self.plate = plate
        self.ticket_type = ticket_type
        self.checkin_time = checkin_time
        self.checkout_time = checkout_time
        self.duration = duration
        self.parking_spot = parking_spot
        self.status = status

class History:
    """Đại diện cho một bản ghi lịch sử ra/vào trong bảng `history`."""
    def __init__(self, vehicle_id: str, plate: str, gate: str, event_type: str, id: Optional[int] = None, camera_id: Optional[int] = None, ticket_id: Optional[str] = None, image_url: Optional[str] = None):
        self.id = id
        self.vehicle_id = vehicle_id
        self.plate = plate
        self.gate = gate
        self.camera_id = camera_id
        self.event_type = event_type
        self.ticket_id = ticket_id
        self.image_url = image_url

class Payment:
    """Đại diện cho một giao dịch thanh toán trong bảng `payments`."""
    def __init__(self, ticket_id: str, amount: float, id: Optional[int] = None):
        self.id = id
        self.ticket_id = ticket_id
        self.amount = amount

class Camera:
    """Đại diện cho một camera trong bảng `cameras`."""
    def __init__(self, gate: str, status: str = 'active', id: Optional[int] = None, ip_address: Optional[str] = None):
        self.id = id
        self.gate = gate
        self.ip_address = ip_address
        self.status = status

class Alert:
    """Đại diện cho một cảnh báo trong bảng `alerts`."""
    def __init__(self, alert_type: str, message: str, severity: str = 'info', resolved: int = 0, id: Optional[int] = None):
        self.id = id
        self.alert_type = alert_type
        self.message = message
        self.severity = severity
        self.resolved = resolved

# --- LỚP QUẢN LÝ DATABASE ---

class DatabaseManager:
    """
    Cung cấp một giao diện để thực hiện các thao tác CRUD (Create, Read, Update, Delete)
    với cơ sở dữ liệu SQLite cho hệ thống quản lý bãi xe.
    """
    def __init__(self, db_path: str):
        """
        Khởi tạo DatabaseManager.
        :param db_path: Đường dẫn đến file database SQLite.
        """
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        """Tạo và trả về một kết nối đến database."""
        conn = sqlite3.connect(self.db_path)
        # Trả về kết quả dưới dạng dictionary-like object thay vì tuple
        conn.row_factory = sqlite3.Row
        return conn

    # --- Phương thức cho Bảng ParkingLot ---

    def create_parking_lot(self, lot: ParkingLot) -> int:
        """Thêm một bãi xe mới vào database."""
        sql = """
            INSERT INTO parking_lot (name, capacity, location, current_occupancy)
            VALUES (?, ?, ?, ?)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (lot.name, lot.capacity, lot.location, lot.current_occupancy))
            conn.commit()
            return cursor.lastrowid

    def get_parking_lot_by_id(self, lot_id: int) -> Optional[ParkingLot]:
        """Lấy thông tin bãi xe bằng ID."""
        sql = "SELECT * FROM parking_lot WHERE id = ?"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (lot_id,))
            row = cursor.fetchone()
            return ParkingLot(**row) if row else None

    def get_all_parking_lots(self) -> List[ParkingLot]:
        """Lấy danh sách tất cả các bãi xe."""
        sql = "SELECT * FROM parking_lot"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [ParkingLot(**row) for row in rows]

    def update_parking_lot(self, lot: ParkingLot) -> bool:
        """Cập nhật thông tin một bãi xe."""
        sql = """
            UPDATE parking_lot
            SET name = ?, capacity = ?, location = ?, current_occupancy = ?
            WHERE id = ?
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, (lot.name, lot.capacity, lot.location, lot.current_occupancy, lot.id))
            conn.commit()
            return cursor.rowcount > 0

    # --- Phương thức cho Bảng Vehicles ---

    def create_vehicle(self, vehicle: Vehicle) -> str:
        """Thêm một phương tiện mới."""
        sql = """
            INSERT INTO vehicles (id, plate, owner_name, owner_phone, vehicle_type, license_plate_image, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        with self._get_connection() as conn:
            conn.execute(sql, (vehicle.id, vehicle.plate, vehicle.owner_name, vehicle.owner_phone, vehicle.vehicle_type, vehicle.license_plate_image, vehicle.created_at))
            conn.commit()
        return vehicle.id

    def get_vehicle_by_plate(self, plate: str) -> Optional[Vehicle]:
        """Lấy thông tin phương tiện bằng biển số xe."""
        sql = "SELECT * FROM vehicles WHERE plate = ?"
        with self._get_connection() as conn:
            row = conn.execute(sql, (plate,)).fetchone()
            return Vehicle(**row) if row else None

    def get_all_vehicles(self) -> List[Vehicle]:
        """Lấy danh sách tất cả các phương tiện."""
        sql = "SELECT * FROM vehicles"
        with self._get_connection() as conn:
            rows = conn.execute(sql).fetchall()
            return [Vehicle(**row) for row in rows]

    def update_vehicle(self, vehicle: Vehicle) -> bool:
        """Cập nhật thông tin phương tiện."""
        sql = """
            UPDATE vehicles
            SET plate = ?, owner_name = ?, owner_phone = ?, vehicle_type = ?, license_plate_image = ?
            WHERE id = ?
        """
        with self._get_connection() as conn:
            cursor = conn.execute(sql, (vehicle.plate, vehicle.owner_name, vehicle.owner_phone, vehicle.vehicle_type, vehicle.license_plate_image, vehicle.id))
            conn.commit()
            return cursor.rowcount > 0

    # --- Phương thức cho Bảng Tickets ---

    def create_ticket(self, ticket: Ticket) -> str:
        """Tạo một vé xe mới."""
        sql = """
            INSERT INTO tickets (id, vehicle_id, plate, ticket_type, checkin_time, checkout_time, duration, parking_spot, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        with self._get_connection() as conn:
            conn.execute(sql, (ticket.id, ticket.vehicle_id, ticket.plate, ticket.ticket_type, ticket.checkin_time, ticket.checkout_time, ticket.duration, ticket.parking_spot, ticket.status))
            conn.commit()
        return ticket.id

    def get_ticket_by_id(self, ticket_id: str) -> Optional[Ticket]:
        """Lấy thông tin vé bằng ID."""
        sql = "SELECT * FROM tickets WHERE id = ?"
        with self._get_connection() as conn:
            row = conn.execute(sql, (ticket_id,)).fetchone()
            return Ticket(**row) if row else None
            
    def get_active_ticket_by_plate(self, plate: str) -> Optional[Ticket]:
        """Lấy vé đang hoạt động (chưa ra) của một biển số xe."""
        sql = "SELECT * FROM tickets WHERE plate = ? AND status = 'active'"
        with self._get_connection() as conn:
            row = conn.execute(sql, (plate,)).fetchone()
            return Ticket(**row) if row else None

    def get_all_tickets(self) -> List[Ticket]:
        """Lấy tất cả các vé xe."""
        sql = "SELECT * FROM tickets"
        with self._get_connection() as conn:
            rows = conn.execute(sql).fetchall()
            return [Ticket(**row) for row in rows]

    def update_ticket(self, ticket: Ticket) -> bool:
        """Cập nhật thông tin vé (ví dụ: khi xe ra, cập nhật checkout_time, status)."""
        sql = """
            UPDATE tickets
            SET vehicle_id = ?, plate = ?, ticket_type = ?, checkin_time = ?,
                checkout_time = ?, duration = ?, parking_spot = ?, status = ?
            WHERE id = ?
        """
        with self._get_connection() as conn:
            cursor = conn.execute(sql, (ticket.vehicle_id, ticket.plate, ticket.ticket_type, ticket.checkin_time, ticket.checkout_time, ticket.duration, ticket.parking_spot, ticket.status, ticket.id))
            conn.commit()
            return cursor.rowcount > 0

    # --- Phương thức cho Bảng History ---

    def create_history_event(self, event: History) -> int:
        """Ghi lại một sự kiện ra/vào."""
        sql = """
            INSERT INTO history (vehicle_id, plate, gate, camera_id, event_type, ticket_id, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        with self._get_connection() as conn:
            cursor = conn.execute(sql, (event.vehicle_id, event.plate, event.gate, event.camera_id, event.event_type, event.ticket_id, event.image_url))
            conn.commit()
            return cursor.lastrowid

    def get_history_for_vehicle(self, vehicle_id: str) -> List[History]:
        """Lấy lịch sử ra/vào của một phương tiện."""
        sql = "SELECT * FROM history WHERE vehicle_id = ?"
        with self._get_connection() as conn:
            rows = conn.execute(sql, (vehicle_id,)).fetchall()
            return [History(**row) for row in rows]

    def get_all_history(self) -> List[History]:
        """Lấy toàn bộ lịch sử ra/vào."""
        sql = "SELECT * FROM history"
        with self._get_connection() as conn:
            rows = conn.execute(sql).fetchall()
            return [History(**row) for row in rows]

    # --- Phương thức cho Bảng Payments ---

    def create_payment(self, payment: Payment) -> int:
        """Tạo một bản ghi thanh toán mới."""
        sql = "INSERT INTO payments (ticket_id, amount) VALUES (?, ?)"
        with self._get_connection() as conn:
            cursor = conn.execute(sql, (payment.ticket_id, payment.amount))
            conn.commit()
            return cursor.lastrowid

    def get_payments_for_ticket(self, ticket_id: str) -> List[Payment]:
        """Lấy các thanh toán của một vé."""
        sql = "SELECT * FROM payments WHERE ticket_id = ?"
        with self._get_connection() as conn:
            rows = conn.execute(sql, (ticket_id,)).fetchall()
            return [Payment(**row) for row in rows]

    # --- Phương thức cho Bảng Cameras ---

    def create_camera(self, camera: Camera) -> int:
        """Thêm một camera mới."""
        sql = "INSERT INTO cameras (gate, ip_address, status) VALUES (?, ?, ?)"
        with self._get_connection() as conn:
            cursor = conn.execute(sql, (camera.gate, camera.ip_address, camera.status))
            conn.commit()
            return cursor.lastrowid

    def get_all_cameras(self) -> List[Camera]:
        """Lấy danh sách tất cả camera."""
        sql = "SELECT * FROM cameras"
        with self._get_connection() as conn:
            rows = conn.execute(sql).fetchall()
            return [Camera(**row) for row in rows]

    def update_camera(self, camera: Camera) -> bool:
        """Cập nhật thông tin camera."""
        sql = "UPDATE cameras SET gate = ?, ip_address = ?, status = ? WHERE id = ?"
        with self._get_connection() as conn:
            cursor = conn.execute(sql, (camera.gate, camera.ip_address, camera.status, camera.id))
            conn.commit()
            return cursor.rowcount > 0

    # --- Phương thức cho Bảng Alerts ---

    def create_alert(self, alert: Alert) -> int:
        """Tạo một cảnh báo mới."""
        sql = "INSERT INTO alerts (alert_type, message, severity, resolved) VALUES (?, ?, ?, ?)"
        with self._get_connection() as conn:
            cursor = conn.execute(sql, (alert.alert_type, alert.message, alert.severity, alert.resolved))
            conn.commit()
            return cursor.lastrowid

    def get_all_alerts(self, resolved: Optional[bool] = None) -> List[Alert]:
        """
        Lấy danh sách cảnh báo.
        :param resolved: Lọc theo trạng thái đã xử lý (True), chưa xử lý (False), hoặc tất cả (None).
        """
        sql = "SELECT * FROM alerts"
        params = []
        if resolved is not None:
            sql += " WHERE resolved = ?"
            params.append(1 if resolved else 0)
            
        with self._get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
            return [Alert(**row) for row in rows]

    def update_alert(self, alert: Alert) -> bool:
        """Cập nhật một cảnh báo (thường là để đánh dấu đã xử lý)."""
        sql = "UPDATE alerts SET alert_type = ?, message = ?, severity = ?, resolved = ? WHERE id = ?"
        with self._get_connection() as conn:
            cursor = conn.execute(sql, (alert.alert_type, alert.message, alert.severity, alert.resolved, alert.id))
            conn.commit()
            return cursor.rowcount > 0
    def get_latest_history(self, event_type: str) -> Optional[dict]:
        """
        Lấy bản ghi history mới nhất theo event_type.
        """
        sql = """
            SELECT *
            FROM history
            WHERE event_type = ?
            ORDER BY id DESC
            LIMIT 1
        """
        with self._get_connection() as conn:
            row = conn.execute(sql, (event_type,)).fetchone()
            return dict(row) if row else None
        
    def get_recent_history(self, limit: int = 10) -> list[dict]:
        """Lấy danh sách các sự kiện lịch sử gần đây nhất."""
        
        # <<< SỬA LỖI TẠI ĐÂY: Sắp xếp theo 'id' thay vì 'timestamp'
        sql = """
            SELECT * FROM history
            ORDER BY id DESC 
            LIMIT ?
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (limit,))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            print(f"Lỗi database khi lấy lịch sử gần đây: {e}")
            return []