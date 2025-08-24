# FILE: client/frontend/traCuu.py (PHIÊN BẢN CẬP NHẬT)
import sys
import asyncio
import aiohttp
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget
)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Qt

# --- Lấy màu từ project ---
C_DARK   = "#13293d"
C_BG     = "#006494"
C_CARD   = "#247ba0"
C_HILITE = "#1b98e0"
C_LIGHT  = "#e8f1f2"
API_URL = "http://localhost:8000/api"

class TraCuuPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {C_BG}; color: {C_LIGHT};")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 20)
        main_layout.setSpacing(15)

        # --- Thanh tìm kiếm và các nút ---
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Nhập biển số xe hoặc mã vé...")
        self.search_input.setFont(QFont("Arial", 14))
        self.search_input.setStyleSheet(f"background-color: {C_LIGHT}; color: #000; padding: 8px; border-radius: 5px;")
        
        self.search_button = QPushButton("Tra cứu")
        self.search_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.search_button.setStyleSheet(f"background-color: {C_HILITE}; color: white; padding: 10px 20px; border-radius: 5px;")
        self.search_button.setCursor(Qt.PointingHandCursor)
        
        # <<< THÊM MỚI: Nút Reset
        self.reset_button = QPushButton("Làm mới")
        self.reset_button.setFont(QFont("Arial", 12, QFont.Bold))
        self.reset_button.setStyleSheet(f"background-color: {C_CARD}; color: white; padding: 10px 20px; border-radius: 5px;")
        self.reset_button.setCursor(Qt.PointingHandCursor)
        
        search_layout.addWidget(self.search_input, 1) # Cho phép ô input co giãn
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.reset_button) # Thêm nút reset vào layout
        
        # --- Label kết quả ---
        self.results_label = QLabel("Đang tải dữ liệu ban đầu...")
        self.results_label.setFont(QFont("Arial", 14, QFont.Bold))
        
        # --- Tab hiển thị kết quả ---
        self.tabs = QTabWidget()
        
        # <<< THAY ĐỔI: Chuyển tất cả các tab thành bảng
        self.vehicles_table = self._create_table(["Biển Số", "Loại Xe", "Chủ Xe", "SĐT", "Ngày Tạo"])
        self.tickets_table = self._create_table(["Mã Vé", "Biển Số", "Loại Vé", "Giờ Vào", "Giờ Ra", "Thời Lượng (phút)", "Trạng Thái"])
        self.history_table = self._create_table(["Biển Số", "Loại Sự Kiện", "Cổng", "Thời Gian", "Mã Vé"])
        self.payments_table = self._create_table(["Mã Thanh Toán", "Mã Vé", "Số Tiền (VNĐ)"])
        
        self.tabs.addTab(self.vehicles_table, "Danh Sách Phương Tiện")
        self.tabs.addTab(self.tickets_table, "Danh Sách Vé Xe")
        self.tabs.addTab(self.history_table, "Lịch Sử Ra/Vào")
        self.tabs.addTab(self.payments_table, "Lịch Sử Thanh Toán")

        self.tabs.setStyleSheet(f"""
            QTabBar::tab {{ background: {C_CARD}; color: {C_LIGHT}; padding: 10px 25px; font-size: 14px;}}
            QTabBar::tab:selected {{ background: {C_HILITE}; font-weight: bold; }}
            QTabWidget::pane {{ border: 1px solid {C_HILITE}; }}
        """)

        main_layout.addLayout(search_layout)
        main_layout.addWidget(self.results_label)
        main_layout.addWidget(self.tabs, 1)

        # --- Kết nối tín hiệu ---
        self.search_button.clicked.connect(self.on_search_clicked)
        self.search_input.returnPressed.connect(self.on_search_clicked)
        self.reset_button.clicked.connect(self.on_reset_clicked) # Kết nối nút reset

    def _create_table(self, headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setStyleSheet(f'QHeaderView::section{{background-color:{C_DARK};color:white;padding:6px;border:none;font-weight:bold;}} QTableWidget{{background-color:{C_CARD};color:white;gridline-color:{C_LIGHT}30;}}')
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        return table

    def on_search_clicked(self):
        query = self.search_input.text()
        if not query:
            self.results_label.setText("Vui lòng nhập thông tin để tra cứu.")
            return
        
        self.results_label.setText(f"Đang tìm kiếm '{query}'...")
        self._clear_all_tables()
        asyncio.create_task(self.fetch_search_data(query))

    # <<< THÊM MỚI: Hàm xử lý nút Reset
    def on_reset_clicked(self):
        self.search_input.clear()
        self.load_initial_data()

    # <<< THÊM MỚI: Hàm tải dữ liệu ban đầu
    def load_initial_data(self):
        self.results_label.setText("Đang tải toàn bộ dữ liệu...")
        self._clear_all_tables()
        asyncio.create_task(self.fetch_all_data())

    async def fetch_all_data(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_URL}/data/all") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.results_label.setText("Hiển thị toàn bộ dữ liệu.")
                        self.update_ui_with_data(data, is_initial_load=True)
                    else:
                        self.results_label.setText(f"Lỗi tải dữ liệu ban đầu (mã lỗi {resp.status}).")
        except Exception as e:
            self.results_label.setText(f"Lỗi kết nối: {e}")

    async def fetch_search_data(self, query: str):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_URL}/search", params={"query": query}) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if not data.get("vehicle"):
                            self.results_label.setText(f"Không tìm thấy kết quả cho '{query}'.")
                        else:
                            self.results_label.setText(f"Hiển thị kết quả cho: {data.get('search_plate')}")
                            self.update_ui_with_data(data, is_initial_load=False)
                    else:
                        self.results_label.setText(f"Lỗi tìm kiếm (mã lỗi {resp.status}).")
        except Exception as e:
            self.results_label.setText(f"Lỗi kết nối: {e}")
            
    def start_initial_fetch(self):
        """Hàm này sẽ được gọi từ bên ngoài sau khi event loop đã chạy."""
        self.results_label.setText("Đang tải toàn bộ dữ liệu...")
        self._clear_all_tables()
        asyncio.create_task(self.fetch_all_data()) # Sửa lại để fetch trang đầu tiên

    def on_reset_clicked(self):
        self.search_input.clear()
        self.start_initial_fetch() 
    # <<< THAY ĐỔI: Cập nhật hàm này để xử lý cả hai trường hợp
    def update_ui_with_data(self, data: dict, is_initial_load: bool):
        if is_initial_load:
            # Tải toàn bộ dữ liệu
            vehicles_data = data.get("vehicles", [])
            self._populate_table(self.vehicles_table, vehicles_data, 
                ["plate", "vehicle_type", "owner_name", "owner_phone", "created_at"], is_time_col=[4])
        else:
            # Kết quả tìm kiếm cho một xe
            vehicle_data = data.get("vehicle")
            if vehicle_data:
                self._populate_table(self.vehicles_table, [vehicle_data], 
                    ["plate", "vehicle_type", "owner_name", "owner_phone", "created_at"], is_time_col=[4])

        self._populate_table(self.tickets_table, data.get("tickets", []), 
            ["id", "plate", "ticket_type", "checkin_time", "checkout_time", "duration", "status"], is_time_col=[3, 4])
            
        self._populate_table(self.history_table, data.get("history", []), 
            ["plate", "event_type", "gate", "timestamp", "ticket_id"], is_time_col=[3])
            
        self._populate_table(self.payments_table, data.get("payments", []), 
            ["id", "ticket_id", "amount"], is_numeric_col=[2])

    def _populate_table(self, table: QTableWidget, data: list, keys: list, is_time_col=[], is_numeric_col=[]):
        table.setRowCount(0)
        for row_data in data:
            row_position = table.rowCount()
            table.insertRow(row_position)
            for col, key in enumerate(keys):
                value = row_data.get(key)
                item_text = self._format_cell(value, col, is_time_col, is_numeric_col)
                item = QTableWidgetItem(item_text)
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row_position, col, item)

    def _format_cell(self, value, col_idx, time_cols, numeric_cols):
        if col_idx in time_cols:
            return self._format_time(value)
        if col_idx in numeric_cols and value is not None:
            return f"{value:,.0f}"
        return str(value) if value is not None else "N/A"

    def _clear_all_tables(self):
        self.vehicles_table.setRowCount(0)
        self.tickets_table.setRowCount(0)
        self.history_table.setRowCount(0)
        self.payments_table.setRowCount(0)

    def _format_time(self, time_str: str | None) -> str:
        if not time_str: return "N/A"
        try:
            # Thử parse cả hai định dạng: có 'T' và không có
            if 'T' in time_str:
                 dt_obj = datetime.fromisoformat(time_str)
            else:
                 dt_obj = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            return dt_obj.strftime('%H:%M:%S %d/%m/%Y')
        except (ValueError, TypeError):
            return time_str

if __name__ == '__main__':
    # ... giữ nguyên không đổi ...
    app = QApplication(sys.argv)
    window = TraCuuPage()
    window.resize(1000, 600)
    window.show()
    sys.exit(app.exec())