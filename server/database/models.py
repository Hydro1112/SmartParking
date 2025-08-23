import datetime
from typing import Optional

class ParkingLot:
    """
    Đại diện cho một bãi xe trong bảng `parking_lot`.
    """
    def __init__(
        self,
        name: str,
        capacity: int,
        location: Optional[str] = None,
        current_occupancy: int = 0,
        id: Optional[int] = None
    ):
        self.id = id
        self.name = name
        self.capacity = capacity
        self.location = location
        self.current_occupancy = current_occupancy

    def __repr__(self) -> str:
        return f"<ParkingLot(id={self.id}, name='{self.name}', capacity={self.capacity})>"

# ---

class Vehicle:
    """
    Đại diện cho một phương tiện trong bảng `vehicles`.
    """
    def __init__(
        self,
        id: str,
        plate: str,
        vehicle_type: str,
        license_plate_image: str,
        owner_name: Optional[str] = None,
        owner_phone: Optional[str] = None,
        created_at: Optional[str] = None
    ):
        self.id = id
        self.plate = plate
        self.owner_name = owner_name
        self.owner_phone = owner_phone
        self.vehicle_type = vehicle_type
        self.license_plate_image = license_plate_image
        self.created_at = created_at or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def __repr__(self) -> str:
        return f"<Vehicle(id='{self.id}', plate='{self.plate}', type='{self.vehicle_type}')>"

# ---

class Ticket:
    """
    Đại diện cho một vé xe trong bảng `tickets`.
    """
    def __init__(
        self,
        id: str,
        vehicle_id: str, # Trong schema là INTEGER nhưng trong code seed là TEXT ('V001')
        plate: str,
        ticket_type: str,
        checkin_time: str,
        status: str = 'active',
        checkout_time: Optional[str] = None,
        duration: Optional[int] = None,
        parking_spot: Optional[str] = None
    ):
        self.id = id
        self.vehicle_id = vehicle_id
        self.plate = plate
        self.ticket_type = ticket_type
        self.checkin_time = checkin_time
        self.checkout_time = checkout_time
        self.duration = duration
        self.parking_spot = parking_spot
        self.status = status

    def __repr__(self) -> str:
        return f"<Ticket(id='{self.id}', plate='{self.plate}', status='{self.status}')>"

# ---

class History:
    """
    Đại diện cho một bản ghi lịch sử ra/vào trong bảng `history`.
    """
    def __init__(
        self,
        vehicle_id: str,
        plate: str,
        gate: str,
        event_type: str,
        id: Optional[int] = None,
        camera_id: Optional[int] = None,
        ticket_id: Optional[str] = None,
        image_url: Optional[str] = None
    ):
        self.id = id
        self.vehicle_id = vehicle_id
        self.plate = plate
        self.gate = gate
        self.camera_id = camera_id
        self.event_type = event_type
        self.ticket_id = ticket_id
        self.image_url = image_url

    def __repr__(self) -> str:
        return f"<History(id={self.id}, plate='{self.plate}', event='{self.event_type}')>"

# ---

class Payment:
    """
    Đại diện cho một giao dịch thanh toán trong bảng `payments`.
    """
    def __init__(
        self,
        ticket_id: str,
        amount: float,
        id: Optional[int] = None
    ):
        self.id = id
        self.ticket_id = ticket_id
        self.amount = amount

    def __repr__(self) -> str:
        return f"<Payment(id={self.id}, ticket_id='{self.ticket_id}', amount={self.amount})>"

# ---

class Camera:
    """
    Đại diện cho một camera trong bảng `cameras`.
    """
    def __init__(
        self,
        gate: str,
        status: str = 'active',
        id: Optional[int] = None,
        ip_address: Optional[str] = None
    ):
        self.id = id
        self.gate = gate
        self.ip_address = ip_address
        self.status = status

    def __repr__(self) -> str:
        return f"<Camera(id={self.id}, gate='{self.gate}', status='{self.status}')>"

# ---

class Alert:
    """
    Đại diện cho một cảnh báo trong bảng `alerts`.
    """
    def __init__(
        self,
        alert_type: str,
        message: str,
        severity: str = 'info',
        resolved: int = 0, # Sử dụng int (0 hoặc 1) để tương thích với SQLite
        id: Optional[int] = None
    ):
        self.id = id
        self.alert_type = alert_type
        self.message = message
        self.severity = severity
        self.resolved = resolved

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, type='{self.alert_type}', severity='{self.severity}')>"