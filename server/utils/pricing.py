# FILE: server/utils/pricing.py

from datetime import datetime
from server.database.models import Ticket

# --- Định nghĩa các mức giá ---
HOURLY_SAME_DAY_RATE = 3000   # Giá vé lượt trong ngày
HOURLY_OVERNIGHT_RATE = 10000 # Giá vé lượt nếu qua ngày
MONTHLY_RATE = 60000        # Giá vé tháng

def calculate_price(ticket: Ticket, checkout_time: datetime) -> int:
    """
    Tính toán chi phí cho một vé khi xe ra.
    - Vé tháng: Luôn trả về 0 vì đã trả trước.
    - Vé lượt: Kiểm tra xem có qua ngày không để áp dụng giá phù hợp.
    """
    if ticket.ticket_type == "monthly":
        return 0

    if ticket.ticket_type == "hourly":
        try:
            checkin_time = datetime.fromisoformat(ticket.checkin_time)
            
            # So sánh ngày của checkout_time với checkin_time
            if checkout_time.date() > checkin_time.date():
                return HOURLY_OVERNIGHT_RATE
            else:
                return HOURLY_SAME_DAY_RATE
        except (ValueError, TypeError):
            # Nếu có lỗi parsing thời gian, trả về giá mặc định
            return HOURLY_SAME_DAY_RATE
            
    return 0 # Mặc định cho các loại vé khác (nếu có)