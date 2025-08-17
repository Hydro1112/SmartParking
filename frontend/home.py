import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy,
    QPushButton, QLabel, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve
from PySide6.QtGui import QFont
from PySide6.QtGui import QIcon
from soatVe import SoatVePage

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
        self.soatve_page = SoatVePage()                    # <-- dùng trang thật
        self.thongke_page = self.create_page("Trang Thống kê")
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

    def create_page(self, text):
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel(text)
        label.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(label, alignment=Qt.AlignCenter)
        return page

    def handle_sidebar_click(self, index):
        self.pages.setCurrentIndex(index)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ParkingDashboard()
    win.show()
    sys.exit(app.exec())
