import sys
from typing import Optional
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFrame, QTableWidget, QTableWidgetItem, QSizePolicy, QAbstractItemView, QPushButton
)
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtCore import Qt
import base64
from PySide6.QtGui import QPixmap, QImage


# ---------------- THEME ----------------
C_DARK   = "#13293d"   # sidebar / header
C_BG     = "#006494"   # main background
C_CARD   = "#247ba0"   # standard card
C_HILITE = "#1b98e0"   # highlight card
C_LIGHT  = "#e8f1f2"   # light text/lines


# ----------------- Reusable Widgets -----------------------
class Card(QFrame):
    def __init__(self, title: Optional[str] = None, bg=C_CARD, radius=14, padding=12, title_bg=C_DARK):
        super().__init__()
        self.setObjectName("Card")
        self.setStyleSheet(f'''
            QFrame#Card {{
                background-color: {bg};
                border-radius: {radius}px;
            }}
        ''')
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(padding, padding, padding, padding)
        self.v.setSpacing(10)
        if title:
            tb = QFrame()
            tb.setStyleSheet(f"background-color: {title_bg}; border-radius: 10px;")
            tl = QHBoxLayout(tb)
            tl.setContentsMargins(12, 8, 12, 8)
            t = QLabel(title)
            t.setStyleSheet("color: white;")
            t.setFont(QFont("Inter, Arial", 16, QFont.Bold))
            tl.addWidget(t)
            self.v.addWidget(tb)


class VideoCard(Card):
    def __init__(self, title: Optional[str] = None, bg=C_CARD):
        super().__init__(title=title, bg=bg)
        self.video = QLabel("Đang khởi tạo camera...")
        self.video.setAlignment(Qt.AlignCenter)
        self.video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video.setStyleSheet("background-color: black; color: white; font-size:14px;")
        self.v.addWidget(self.video)


# ----------------- Main Window -----------------------
class SoatVePage(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Soát vé - Smart Parking")
        self.resize(1400, 800)

        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(C_BG))
        self.setPalette(pal)

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        main = QFrame()
        main.setStyleSheet(f"background-color:{C_BG};")
        m = QVBoxLayout(main)
        m.setContentsMargins(16, 10, 16, 16)
        m.setSpacing(10)

        title = QLabel("Soát vé")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Inter, Arial", 20, QFont.Black))
        title.setStyleSheet("color:white;")
        m.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        m.addLayout(grid, 1)

        # Camera trái/phải
        self.cam_left  = VideoCard(bg=C_CARD)
        self.cam_right = VideoCard(bg=C_CARD)
        grid.addWidget(self.cam_left,  0, 0, 1, 1)
        grid.addWidget(self.cam_right, 0, 3, 1, 1)

        # Khung xe vào
        self.card_in = Card(title="Xe vào", bg=C_CARD)
        self.label_in_info = QLabel("Chưa có dữ liệu")
        self.label_in_info.setStyleSheet(f"color:{C_LIGHT};")
        self.card_in.v.addWidget(self.label_in_info)

        self.label_in_plate_img = QLabel()
        self.label_in_plate_img.setAlignment(Qt.AlignCenter)
        self.label_in_plate_img.setFixedHeight(120)
        self.card_in.v.addWidget(self.label_in_plate_img)

        self.label_in_plate_text = QLabel("Biển số: ---")
        self.label_in_plate_text.setAlignment(Qt.AlignCenter)
        self.label_in_plate_text.setStyleSheet("color:white; font-weight:700;")
        self.card_in.v.addWidget(self.label_in_plate_text)

        # Khung xe ra
        self.card_out = Card(title="Xe ra", bg=C_CARD)
        self.label_out_info = QLabel("Chưa có dữ liệu")
        self.label_out_info.setStyleSheet(f"color:{C_LIGHT};")
        self.card_out.v.addWidget(self.label_out_info)

        self.label_out_plate_img = QLabel()
        self.label_out_plate_img.setAlignment(Qt.AlignCenter)
        self.label_out_plate_img.setFixedHeight(120)
        self.card_out.v.addWidget(self.label_out_plate_img)

        self.label_out_plate_text = QLabel("Biển số: ---")
        self.label_out_plate_text.setAlignment(Qt.AlignCenter)
        self.label_out_plate_text.setStyleSheet("color:white; font-weight:700;")
        self.card_out.v.addWidget(self.label_out_plate_text)

        # Camera giữa
        self.mid_cam_in  = VideoCard(title="Camera vào", bg=C_CARD)
        self.mid_cam_out = VideoCard(title="Camera ra", bg=C_CARD)

        grid.addWidget(self.card_in,      1, 0, 2, 1)
        grid.addWidget(self.mid_cam_in,  1, 1, 1, 1)
        grid.addWidget(self.mid_cam_out, 1, 2, 1, 1)
        grid.addWidget(self.card_out,     1, 3, 2, 1)

        # Table xe gần đây
        self.recent = Card(title="Xe gần đây", bg=C_HILITE)
        self.table_recent = QTableWidget(0, 3)
        self.table_recent.setHorizontalHeaderLabels(["Biển số", "Trạng thái", "Thời gian"])
        self.table_recent.verticalHeader().setVisible(False)
        self.table_recent.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_recent.setSelectionMode(QAbstractItemView.NoSelection)
        self.table_recent.setStyleSheet(f'''
            QHeaderView::section {{
                background-color: {C_DARK};
                color: white;
                padding: 6px;
                border: none;
            }}
            QTableWidget {{
                background-color: transparent;
                color: white;
                gridline-color: {C_LIGHT};
            }}
        ''')
        self.table_recent.resizeColumnsToContents()
        self.recent.v.addWidget(self.table_recent)

        grid.addWidget(self.recent, 2, 1, 1, 2)
        root_layout.addWidget(main, 1)
    def update_vehicle_info(self, direction: str, data: Optional[dict]):
        """Cập nhật card xe vào/ra."""
        if direction == "in":
            label_info = self.label_in_info
            label_plate = self.label_in_plate_text
            label_img = self.label_in_plate_img
        else:
            label_info = self.label_out_info
            label_plate = self.label_out_plate_text
            label_img = self.label_out_plate_img

        if not data:
            label_info.setText("Chưa có dữ liệu")
            label_plate.setText("Biển số: ---")
            label_img.clear()
            return

        plate = data.get("plate", "---")
        vtype = data.get("vehicle_type", "---")
        ttype = data.get("ticket_type", "---")
        time  = data.get("time", "---")

        label_info.setText(f"Loại xe: {vtype} | Vé: {ttype}\nThời gian: {time}")
        label_plate.setText(f"Biển số: {plate}")

        # hiển thị ảnh biển số (nếu có)
        b64img = data.get("license_plate_image")
        if b64img:
            try:
                img_bytes = base64.b64decode(b64img)
                image = QImage.fromData(img_bytes)
                pixmap = QPixmap.fromImage(image)
                label_img.setPixmap(pixmap.scaled(
                    label_img.width(), label_img.height(),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
            except Exception as e:
                print("Decode ảnh lỗi:", e)
                label_img.clear()
        else:
            label_img.clear()

        # Ghi thêm vào bảng xe gần đây
        self.add_recent(plate, data.get("event_type", "---"), time)
    def add_recent(self, plate: str, status: str, time: str):
        """Thêm xe vào bảng 'Xe gần đây' (hiển thị 10 xe mới nhất)."""
        row = self.table_recent.rowCount()
        self.table_recent.insertRow(0)  # thêm ở đầu bảng
        self.table_recent.setItem(0, 0, QTableWidgetItem(plate))
        self.table_recent.setItem(0, 1, QTableWidgetItem(status))
        self.table_recent.setItem(0, 2, QTableWidgetItem(time))

        # giữ tối đa 10 dòng
        if row >= 10:
            self.table_recent.removeRow(row)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = SoatVePage()
    win.show()
    sys.exit(app.exec())
