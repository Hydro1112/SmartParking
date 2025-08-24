import sqlite3
import datetime
from pathlib import Path
from typing import List, Optional, Any
import pandas as pd

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
    def __init__(self, vehicle_id: str, plate: str, gate: str, event_type: str, timestamp: str, id: Optional[int] = None, camera_id: Optional[int] = None, ticket_id: Optional[str] = None):
        self.id = id
        self.vehicle_id = vehicle_id
        self.plate = plate
        self.gate = gate
        self.camera_id = camera_id
        self.event_type = event_type
        self.ticket_id = ticket_id
        self.timestamp = timestamp

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
            INSERT INTO history (vehicle_id, plate, gate, camera_id, event_type, ticket_id, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        with self._get_connection() as conn:
            cursor = conn.execute(sql, (event.vehicle_id, event.plate, event.gate, event.camera_id, event.event_type, event.ticket_id, event.timestamp))
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
        
    def get_active_monthly_ticket_by_plate(self, plate: str) -> Optional[Ticket]:
        """Lấy vé tháng đang hoạt động (chưa hết hạn) của một biển số xe."""
        # Lưu ý: Logic 'hết hạn' có thể phức tạp hơn, 
        # ở đây ta giả định 'active' là đủ.
        sql = "SELECT * FROM tickets WHERE plate = ? AND status = 'active' AND ticket_type = 'monthly'"
        with self._get_connection() as conn:
            row = conn.execute(sql, (plate,)).fetchone()
            return Ticket(**row) if row else None
        
    def get_dashboard_statistics(self, start_date: str, end_date: str) -> dict:
        """
        Tổng hợp tất cả dữ liệu thống kê cho dashboard trong một khoảng thời gian.
        Sử dụng Pandas để tăng tốc độ xử lý.
        """
        with self._get_connection() as conn:
            # --- 1. Lấy dữ liệu thô từ các bảng liên quan ---
            
            # Lịch sử vào ra cho biểu đồ
            history_df = pd.read_sql_query(
                "SELECT timestamp, event_type FROM history WHERE timestamp BETWEEN ? AND ?",
                conn, params=(start_date, end_date)
            )
            # Thanh toán và thời gian checkout để tính doanh thu
            payments_df = pd.read_sql_query(
                """
                SELECT p.amount, t.checkout_time
                FROM payments p JOIN tickets t ON p.ticket_id = t.id
                WHERE t.checkout_time BETWEEN ? AND ?
                """,
                conn, params=(start_date, end_date)
            )
            # Vé đã đóng để tính thời gian gửi trung bình
            closed_tickets_df = pd.read_sql_query(
                "SELECT duration FROM tickets WHERE status = 'closed' AND checkout_time BETWEEN ? AND ?",
                conn, params=(start_date, end_date)
            )

            # --- 2. Tính toán các chỉ số KPI ---
            
            # Tỷ lệ lấp đầy (không phụ thuộc thời gian)
            occupancy_data = conn.execute("SELECT SUM(current_occupancy), SUM(capacity) FROM parking_lot").fetchone()
            
            # Vé đang hoạt động (không phụ thuộc thời gian)
            active_tickets_count = conn.execute("SELECT COUNT(*) FROM tickets WHERE status = 'active'").fetchone()[0]

            kpis = {
                "occupancy": {
                    "current": occupancy_data[0] or 0,
                    "capacity": occupancy_data[1] or 1,
                },
                "revenue": payments_df['amount'].sum(),
                "active_tickets": active_tickets_count,
                "avg_dwell_time_minutes": closed_tickets_df['duration'].mean()
            }

            # --- 3. Chuẩn bị dữ liệu cho biểu đồ ---
            
            # Biểu đồ Lượt vào/ra
            traffic_chart = {}
            if not history_df.empty:
                history_df['timestamp'] = pd.to_datetime(history_df['timestamp'])
                history_df.set_index('timestamp', inplace=True)
                daily_traffic = history_df.groupby([history_df.index.date, 'event_type']).size().unstack(fill_value=0)
                daily_traffic.index = pd.to_datetime(daily_traffic.index)
                # Tạo dải ngày đầy đủ để không bị thiếu ngày
                full_date_range = pd.date_range(start=start_date.split('T')[0], end=end_date.split('T')[0], freq='D')
                daily_traffic = daily_traffic.reindex(full_date_range.date, fill_value=0)
                
                traffic_chart = {
                    "dates": [d.strftime('%Y-%m-%d') for d in daily_traffic.index],
                    "in_counts": daily_traffic.get('in', pd.Series(0, index=daily_traffic.index)).tolist(),
                    "out_counts": daily_traffic.get('out', pd.Series(0, index=daily_traffic.index)).tolist(),
                }
            
            # Biểu đồ Doanh thu
            revenue_chart = {}
            if not payments_df.empty:
                payments_df['checkout_time'] = pd.to_datetime(payments_df['checkout_time'])
                payments_df.set_index('checkout_time', inplace=True)
                daily_revenue = payments_df.resample('D')['amount'].sum()
                revenue_chart = {
                    "dates": [d.strftime('%Y-%m-%d') for d in daily_revenue.index],
                    "amounts": daily_revenue.values.tolist()
                }

            # Biểu đồ nhiệt Mật độ
            heatmap_chart = [[0] * 24 for _ in range(7)] # 7 ngày x 24 giờ
            if not history_df.empty and 'in' in history_df['event_type'].unique():
                checkins_df = history_df[history_df['event_type'] == 'in']
                # index 0 = Monday, 6 = Sunday for dayofweek
                checkins_df['day_of_week'] = checkins_df.index.dayofweek
                checkins_df['hour'] = checkins_df.index.hour
                density = checkins_df.groupby(['day_of_week', 'hour']).size().unstack(fill_value=0)
                # Điền dữ liệu vào ma trận heatmap
                for day, row in density.iterrows():
                    for hour, count in row.items():
                        heatmap_chart[day][hour] = count

            # --- 4. Lấy thông tin phụ ---

            # Tình trạng vé (không phụ thuộc thời gian)
            ticket_status_rows = conn.execute("SELECT ticket_type, status, COUNT(*) FROM tickets GROUP BY ticket_type, status").fetchall()
            ticket_status = [{"type": row[0], "status": row[1], "count": row[2]} for row in ticket_status_rows]
            
            # Cảnh báo chưa xử lý
            alert_rows = conn.execute("SELECT message, severity FROM alerts WHERE resolved = 0 ORDER BY id DESC LIMIT 5").fetchall()
            alerts = [{"message": row[0], "severity": row[1]} for row in alert_rows]

            return {
                "kpis": kpis,
                "charts": {
                    "traffic": traffic_chart,
                    "revenue": revenue_chart,
                    "heatmap": heatmap_chart
                },
                "other": {
                    "ticket_status": ticket_status,
                    "alerts": alerts
                }
            }
            
    def get_tickets_by_plate(self, plate: str) -> List[Ticket]:
        """Lấy tất cả vé xe (cả active và closed) của một biển số xe."""
        sql = "SELECT * FROM tickets WHERE plate = ? ORDER BY checkin_time DESC"
        with self._get_connection() as conn:
            rows = conn.execute(sql, (plate,)).fetchall()
            return [Ticket(**row) for row in rows]

    def get_history_by_plate(self, plate: str) -> List[History]:
        """Lấy toàn bộ lịch sử ra/vào của một biển số xe."""
        sql = "SELECT * FROM history WHERE plate = ? ORDER BY timestamp DESC"
        with self._get_connection() as conn:
            rows = conn.execute(sql, (plate,)).fetchall()
            return [History(**row) for row in rows]

    def get_payments_by_ticket_ids(self, ticket_ids: List[str]) -> List[Payment]:
        """Lấy các thanh toán dựa trên một danh sách các mã vé."""
        if not ticket_ids:
            return []
        placeholders = ','.join('?' for _ in ticket_ids)
        sql = f"SELECT * FROM payments WHERE ticket_id IN ({placeholders})"
        with self._get_connection() as conn:
            rows = conn.execute(sql, ticket_ids).fetchall()
            return [Payment(**row) for row in rows]
        
    def get_all_payments(self) -> List[Payment]:
        """Lấy toàn bộ lịch sử thanh toán."""
        sql = "SELECT * FROM payments ORDER BY id DESC"
        with self._get_connection() as conn:
            rows = conn.execute(sql).fetchall()
            return [Payment(**row) for row in rows]