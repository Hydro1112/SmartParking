# FILE: frontend/soatVe.py (PHIÊN BẢN SỬA LỖI HIỂN THỊ CHỈ Ở CLIENT)
# ----------------------------------------------------------------------
import sys
import base64
from typing import Optional
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFrame, QTableWidget, QTableWidgetItem, QSizePolicy, QAbstractItemView,
    QHeaderView
)
from PySide6.QtGui import QFont, QColor, QPalette, QPixmap
from PySide6.QtCore import Qt, QSize

# ---------------- THEME ----------------
C_DARK, C_BG, C_CARD, C_HILITE, C_LIGHT = "#13293d", "#006494", "#247ba0", "#1b98e0", "#e8f1f2"

# ----------------- Reusable Widgets -----------------------
class Card(QFrame):
    def __init__(self, title: Optional[str] = None, bg=C_CARD, radius=14, padding=12, title_bg=C_DARK):
        super().__init__()
        self.setObjectName("Card")
        self.setStyleSheet(f'QFrame#Card {{ background-color: {bg}; border-radius: {radius}px; }}')
        self.v = QVBoxLayout(self); self.v.setContentsMargins(padding, padding, padding, padding); self.v.setSpacing(10)
        if title:
            tb = QFrame(); tb.setStyleSheet(f"background-color: {title_bg}; border-radius: 10px;")
            tl = QHBoxLayout(tb); tl.setContentsMargins(12, 8, 12, 8)
            t = QLabel(title); t.setStyleSheet("color: white;"); t.setFont(QFont("Inter, Arial", 16, QFont.Bold))
            tl.addWidget(t); self.v.addWidget(tb)

class VideoCard(Card):
    def __init__(self, title: Optional[str] = None, bg=C_CARD):
        super().__init__(title=title, bg=bg)
        self.video = QLabel("Đang khởi tạo camera..."); self.video.setAlignment(Qt.AlignCenter)
        self.video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video.setStyleSheet("background-color: black; color: white; font-size:14px;")
        self.v.addWidget(self.video)

# ----------------- Main Window -----------------------
class SoatVePage(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Soát vé - Smart Parking")
        self.resize(1400, 800)
        pal = self.palette(); pal.setColor(QPalette.Window, QColor(C_BG)); self.setPalette(pal)
        
        root_layout = QHBoxLayout(self); root_layout.setContentsMargins(0, 0, 0, 0); root_layout.setSpacing(0)
        main = QFrame(); main.setStyleSheet(f"background-color:{C_BG};"); m = QVBoxLayout(main)
        m.setContentsMargins(16, 10, 16, 16); m.setSpacing(10)
        title = QLabel("Soát vé"); title.setAlignment(Qt.AlignCenter); title.setFont(QFont("Inter, Arial", 20, QFont.Black)); title.setStyleSheet("color:white;"); m.addWidget(title)
        grid = QGridLayout(); grid.setHorizontalSpacing(12); grid.setVerticalSpacing(12); m.addLayout(grid, 1)

        # Khung xe vào
        self.card_in = Card(title="Xe vào", bg=C_CARD)
        self.label_in_info = QLabel("Chưa có dữ liệu"); self.label_in_info.setStyleSheet(f"color:{C_LIGHT}; font-size: 14px;")
        self.card_in.v.addWidget(self.label_in_info)
        
        self.label_in_plate_img = QLabel()
        self.label_in_plate_img.setAlignment(Qt.AlignCenter)
        # <<< THAY ĐỔI 1: Đặt kích thước CỐ ĐỊNH cho vùng chứa ảnh
        self.label_in_plate_img.setFixedSize(520, 300) 
        self.label_in_plate_img.setStyleSheet("background-color: #000; border-radius: 8px; color: white;") # Thêm nền đen
        self.label_in_plate_img.setText("...") # Thêm text chờ
        self.card_in.v.addWidget(self.label_in_plate_img)

        self.label_in_plate_text = QLabel("---"); self.label_in_plate_text.setAlignment(Qt.AlignCenter); self.label_in_plate_text.setFont(QFont("Inter, Arial", 18, QFont.Bold)); self.label_in_plate_text.setStyleSheet("color:white;")
        self.card_in.v.addWidget(self.label_in_plate_text); self.card_in.v.addStretch()

        # Khung xe ra
        self.card_out = Card(title="Xe ra", bg=C_CARD)
        self.label_out_info = QLabel("Chưa có dữ liệu"); self.label_out_info.setStyleSheet(f"color:{C_LIGHT}; font-size: 14px;")
        self.card_out.v.addWidget(self.label_out_info)
        
        self.label_out_plate_img = QLabel()
        self.label_out_plate_img.setAlignment(Qt.AlignCenter)
        # <<< THAY ĐỔI 2: Tương tự cho khung xe ra
        self.label_out_plate_img.setFixedSize(520, 300)
        self.label_out_plate_img.setStyleSheet("background-color: #000; border-radius: 8px; color: white;")
        self.label_out_plate_img.setText("...")
        self.card_out.v.addWidget(self.label_out_plate_img)

        self.label_out_plate_text = QLabel("---"); self.label_out_plate_text.setAlignment(Qt.AlignCenter); self.label_out_plate_text.setFont(QFont("Inter, Arial", 18, QFont.Bold)); self.label_out_plate_text.setStyleSheet("color:white;")
        self.card_out.v.addWidget(self.label_out_plate_text); self.card_out.v.addStretch()

        # ... (Phần layout còn lại của __init__ giữ nguyên)
        self.mid_cam_in  = VideoCard(title="Camera Vào", bg=C_DARK); self.mid_cam_out = VideoCard(title="Camera Ra", bg=C_DARK)
        grid.addWidget(self.card_in, 0, 0, 2, 1); grid.addWidget(self.mid_cam_in,  0, 1, 1, 1); grid.addWidget(self.mid_cam_out, 0, 2, 1, 1); grid.addWidget(self.card_out, 0, 3, 2, 1)
        self.recent = Card(title="Lịch sử gần đây", bg=C_HILITE)
        self.table_recent = QTableWidget(0, 6); self.table_recent.setHorizontalHeaderLabels(["Biển số", "Mã vé", "Loại xe", "Loại vé", "Thời gian", "Trạng thái"]); self.table_recent.verticalHeader().setVisible(False); self.table_recent.setEditTriggers(QAbstractItemView.NoEditTriggers); self.table_recent.setSelectionMode(QAbstractItemView.NoSelection); self.table_recent.setStyleSheet(f'QHeaderView::section{{background-color:{C_DARK};color:white;padding:6px;border:none;font-weight:bold;}} QTableWidget{{background-color:transparent;color:white;gridline-color:{C_LIGHT}30;}}'); self.table_recent.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.recent.v.addWidget(self.table_recent); grid.addWidget(self.recent, 1, 1, 1, 2)
        grid.setColumnStretch(0, 3); grid.setColumnStretch(1, 2); grid.setColumnStretch(2, 2); grid.setColumnStretch(3, 3)
        root_layout.addWidget(main, 1)

    def update_cards(self, latest_in: Optional[dict], latest_out: Optional[dict]):
        self._update_single_card("in", latest_in)
        self._update_single_card("out", latest_out)

    def _update_single_card(self, direction: str, data: Optional[dict]):
        if direction == "in": label_info, label_plate, label_img = self.label_in_info, self.label_in_plate_text, self.label_in_plate_img
        else: label_info, label_plate, label_img = self.label_out_info, self.label_out_plate_text, self.label_out_plate_img

        if not data:
            label_info.setText("Chưa có dữ liệu"); label_plate.setText("---"); label_img.clear(); label_img.setText("..."); return

        plate, vtype, ttype, time, ticket_id = data.get("plate", "---"), data.get("vehicle_type", "---").capitalize(), data.get("ticket_type", "---").capitalize(), data.get("time", "---"), data.get("ticket_id", "---")
        info_text = f"<b style='color:#ffffff;'>Mã vé:</b> {ticket_id}<br>" f"<b style='color:#ffffff;'>Loại xe:</b> {vtype}<br>" f"<b style='color:#ffffff;'>Loại vé:</b> {ttype}<br>" f"<b style='color:#ffffff;'>Thời gian:</b> {time}"
        label_info.setText(info_text); label_plate.setText(plate)

        b64img = data.get("license_plate_image")
        if b64img:
            try:
                img_bytes = base64.b64decode(b64img)
                pixmap = QPixmap()
                pixmap.loadFromData(img_bytes)
                
                # <<< THAY ĐỔI 3: Co giãn pixmap một cách mượt mà để vừa với label CÓ KÍCH THƯỚC CỐ ĐỊNH
                scaled_pixmap = pixmap.scaled(label_img.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label_img.setPixmap(scaled_pixmap)

            except Exception as e:
                print(f"[UI] Lỗi decode ảnh cho biển số {plate}:", e); label_img.clear(); label_img.setText("Lỗi ảnh")
        else:
            label_img.clear(); label_img.setText("...")

    def add_to_history(self, data: dict):
        # ... (Giữ nguyên không đổi)
        if not data: return
        plate, ticket_id, vtype, ttype, time, status = data.get("plate", "---"), data.get("ticket_id", "---"), data.get("vehicle_type", "---").capitalize(), data.get("ticket_type", "---").capitalize(), data.get("time", "---"), data.get("event_type", "---")
        display_status = "Vào" if status == "in" else "Ra"
        if self.table_recent.rowCount() > 0:
            if self.table_recent.item(0, 0).text() == plate and self.table_recent.item(0, 5).text() == display_status: return
        self.table_recent.insertRow(0)
        items = [QTableWidgetItem(plate), QTableWidgetItem(ticket_id), QTableWidgetItem(vtype), QTableWidgetItem(ttype), QTableWidgetItem(time), QTableWidgetItem(display_status)]
        for i, item in enumerate(items): item.setTextAlignment(Qt.AlignCenter); self.table_recent.setItem(0, i, item)
        status_item = self.table_recent.item(0, 5)
        if status == "in": status_item.setBackground(QColor("#1b98e0"))
        else: status_item.setBackground(QColor("#e01b6a"))
        if self.table_recent.rowCount() > 10: self.table_recent.removeRow(10)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SoatVePage()
    win.show()
    sys.exit(app.exec())