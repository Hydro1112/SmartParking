import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy,
    QPushButton, QLabel, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve
from PySide6.QtGui import QFont
from PySide6.QtGui import QIcon
from soatVe import SoatVePage
from stats import StatsPage


class SidebarButton(QPushButton):
    def __init__(self, text, icon_path=None, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        if icon_path:
            self.setIcon(QIcon(icon_path))
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ffffff;
                border: none;
                padding: 12px;
                text-align: center;
                font-size: 25px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton:checked {
                font-weight: bold;
            }
        """)

class Sidebar(QWidget):
    def __init__(self, items, on_click=None, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setStyleSheet("background-color: #13293d;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header / Logo
        header = QLabel("🚗 Smart Parking")
        header.setStyleSheet("color: white; font-size: 18px; font-weight: bold; padding: 16px;")
        header.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(header)

        # Container for buttons
        btn_container = QWidget()
        btn_layout = QVBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 10, 0, 0)
        btn_layout.setSpacing(0)
        main_layout.addWidget(btn_container)

        # Highlight bar
        self.highlight = QFrame(self)
        self.highlight.setStyleSheet("background-color: #1b98e0; border-radius: 3px;")
        self.highlight.setGeometry(QRect(0, 60, 6, 40))
        self.anim = QPropertyAnimation(self.highlight, b"geometry")
        self.anim.setDuration(250)
        
        self.anim = QPropertyAnimation(self.highlight, b"geometry")
        self.anim.setDuration(300)  # Thời gian animation (ms)
        self.anim.setEasingCurve(QEasingCurve.InOutCubic)  # Kiểu chuyển động


        # Buttons
        self.buttons = []
        for item in items:
            if isinstance(item, (tuple, list)) and len(item) == 2:
                text, icon = item
            else:
                text, icon = item, None

            btn = SidebarButton(text, icon)
            index = len(self.buttons)  # lấy index đúng của button
            btn.clicked.connect(lambda checked, b=btn, i=index: (
                self.set_active_button(b),
                on_click(i) if on_click else None
            ))
            btn_layout.addWidget(btn)
            self.buttons.append(btn)

        btn_layout.addStretch(1)

        # Footer
        footer = QLabel("⚙️ Cài đặt | ⏻ Thoát")
        footer.setStyleSheet("color: gray; font-size: 13px; padding: 10px;")
        footer.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(footer)

        if self.buttons:
            self.set_active_button(self.buttons[0])

    def set_active_button(self, active_btn):
        for btn in self.buttons:
            btn.setChecked(False)
        active_btn.setChecked(True)

        # Lấy vị trí tuyệt đối của nút trong Sidebar
        global_pos = active_btn.mapTo(self, active_btn.rect().topLeft())
        y = global_pos.y()

        self.anim.stop()
        self.anim.setStartValue(self.highlight.geometry())
        self.anim.setEndValue(QRect(0, y, 6, active_btn.height()))
        self.anim.start()


class ParkingDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Parking Dashboard")
        self.resize(900, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Sidebar
        self.sidebar = Sidebar(
            ["Soát vé", "Thống kê", "Giám sát", "Dữ liệu"],
            self.handle_sidebar_click,
            parent=self
        )
        self.sidebar.setStyleSheet("background-color: #0A2A43;")
        self.sidebar.setFixedWidth(180)
        
        self.pages = QStackedWidget()
        self.soatve_page = SoatVePage()             
        self.thongke_page = StatsPage()
        self.giamsat_page = self.create_page("Trang Giám sát")
        self.dulieu_page = self.create_page("Trang Dữ liệu")

        self.pages.addWidget(self.soatve_page)   # index 0
        self.pages.addWidget(self.thongke_page)  # index 1
        self.pages.addWidget(self.giamsat_page)  # index 2
        self.pages.addWidget(self.dulieu_page)   # index 3

        layout.addWidget(self.sidebar)
        layout.addWidget(self.pages)

        # Mặc định mở Soát vé
        self.pages.setCurrentIndex(0)

<<<<<<< HEAD
    def create_page(self, text):
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel(text)
        label.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(label, alignment=Qt.AlignCenter)
        return page

    def handle_sidebar_click(self, index):
        self.pages.setCurrentIndex(index)
=======
        # Row 1: camera - progress+pie - camera
        self.cam_left  = VideoCard(bg=C_CARD)
        self.cam_right = VideoCard(bg=C_CARD)
        self.cam_left.setMinimumHeight(250)
        self.cam_right.setMinimumHeight(250)

        mid = Card(bg=C_HILITE, radius=14, padding=14)

        def progress_row(pct, label_text, emoji):
            row = QVBoxLayout()
            head = QHBoxLayout()
            lblpct = QLabel(f"{pct}%")
            lblpct.setStyleSheet("color:white;")
            lblpct.setFont(QFont("Inter, Arial", 15, QFont.Black))
            head.addWidget(lblpct)
            head.addStretch(1)
            ic = QLabel(emoji)
            ic.setFixedWidth(22)
            head.addWidget(ic)
            row.addLayout(head)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(pct)
            bar.setTextVisible(False)
            bar.setFixedHeight(16)
            bar.setStyleSheet(f'''
                QProgressBar {{
                    background-color: rgba(0,0,0,0.25);
                    border-radius: 8px;
                }}
                QProgressBar::chunk {{
                    background-color: {C_DARK};
                    border-radius: 8px;
                }}
            ''')
            row.addWidget(bar)
            sub = QLabel(label_text)
            sub.setStyleSheet("color:white;")
            row.addWidget(sub)
            return row

        leftcol = QVBoxLayout()
        leftcol.addLayout(progress_row(40, "Đã chiếm 40/100 chỗ xe máy", "🛵"))
        leftcol.addSpacing(8)
        leftcol.addLayout(progress_row(60, "Đã chiếm 60/100 chỗ ô tô", "🚗"))
        leftcol.addStretch(1)

        pie = PieChart([75, 25], ["Xe máy", "Ô tô"], [C_DARK, C_BG])
        legend_wrap = QVBoxLayout()
        legend_wrap.addWidget(LegendDot("Tỷ lệ loại xe", "transparent"))
        legend_wrap.addSpacing(4)
        legend_wrap.addWidget(LegendDot("Xe máy", C_DARK))
        legend_wrap.addWidget(LegendDot("Ô tô", C_BG))
        legend_wrap.addStretch(1)
        legend_frame = QFrame()
        legend_frame.setLayout(legend_wrap)

        midrow = QHBoxLayout()
        midrow.addLayout(leftcol, 3)
        midrow.addWidget(pie, 2)
        midrow.addWidget(legend_frame, 1)
        mid.v.addLayout(midrow)

        grid.addWidget(self.cam_left,  0, 0, 1, 1)
        grid.addWidget(self.cam_right, 0, 3, 1, 1)
        grid.addWidget(mid,       0, 1, 1, 2)

        # Row 2-3: Xe vào / Xe ra + camera
        xe_vao = Card(title="Xe vào", bg=C_CARD)
        xe_vao_text = QLabel("Thời gian vào: 21:00 11/08/2025\nLoại xe: Xe máy\nVé: XM001")
        xe_vao_text.setStyleSheet(f"color:{C_LIGHT};")
        xe_vao.v.addWidget(xe_vao_text)
        plate_left = QLabel()
        plate_left.setAlignment(Qt.AlignCenter)
        plate_left.setFixedHeight(120)
        xe_vao.v.addWidget(plate_left)
        cap_vao = QLabel("Biển số:\n29 - G1 333.33")
        cap_vao.setAlignment(Qt.AlignCenter)
        cap_vao.setStyleSheet("color:white; font-weight:700;")
        xe_vao.v.addWidget(cap_vao)

        xe_ra = Card(title="Xe ra", bg=C_CARD)
        xe_ra_text = QLabel("Thời gian ra: 21:00 11/08/2025\nThời gian giữ xe: 4h25p\nGiá vé: 10.000 VND\nLoại xe: Ô tô\nVé: OT001")
        xe_ra_text.setStyleSheet(f"color:{C_LIGHT};")
        xe_ra.v.addWidget(xe_ra_text)
        plate_right = QLabel()
        plate_right.setAlignment(Qt.AlignCenter)
        plate_right.setFixedHeight(120)
        xe_ra.v.addWidget(plate_right)
        cap_ra = QLabel("Biển số: 30G 493.44")
        cap_ra.setAlignment(Qt.AlignCenter)
        cap_ra.setStyleSheet("color:white; font-weight:700;")
        xe_ra.v.addWidget(cap_ra)

        mid_cam_in  = VideoCard(bg=C_CARD)
        mid_cam_out = VideoCard(bg=C_CARD)

        grid.addWidget(xe_vao,      1, 0, 2, 1)
        grid.addWidget(mid_cam_in,  1, 1, 1, 1)
        grid.addWidget(mid_cam_out, 1, 2, 1, 1)
        grid.addWidget(xe_ra,       1, 3, 2, 1)

        # Row 3: Table
        recent = Card(bg=C_HILITE)
        header = QFrame()
        header.setStyleSheet(f"background-color:{C_BG}; border-radius: 10px;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 8, 12, 8)
        htxt = QLabel("Xe gần đây")
        htxt.setStyleSheet("color:white; font-weight:700;")
        hl.addWidget(htxt)
        recent.v.addWidget(header)

        table = QTableWidget(3, 3)
        table.setHorizontalHeaderLabels(["Biển số", "Trạng thái", "Thời gian"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.NoSelection)

        rows = [
            ("20 - G1 123.44", "Ra", "20:59"),
            ("20 - G1 123.45", "Vào", "20:58"),
            ("29 - G1 333.33", "Vào", "20:55"),
        ]
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(r, c, item)

        table.setStyleSheet(f'''
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
        table.resizeColumnsToContents()
        recent.v.addWidget(table)

        grid.addWidget(recent, 2, 1, 1, 2)

        # Compose
        root.addWidget(sidebar)
        root.addWidget(main, 1)


def main():
    app = QApplication(sys.argv)
    w = ParkingDashboard()
    w.show()
    sys.exit(app.exec())
>>>>>>> 11ee62ccf10c9cce6a46e4b126e55bb2f10ab57f


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ParkingDashboard()
    win.show()
    sys.exit(app.exec())
