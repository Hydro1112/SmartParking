# File: client/frontend/home.py (PHIÊN BẢN SỬA LỖI CUỐI CÙNG)

import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt, QPropertyAnimation, QRect, QEasingCurve
from PySide6.QtGui import QFont

from frontend.soatVe import SoatVePage
from frontend.stats import StatsPage
from frontend.cameraCart import CameraPage
from frontend.search import TraCuuPage

class SidebarButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #ffffff; border: none;
                padding: 12px 20px; text-align: left; font-size: 16px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 0.1); }
            QPushButton:checked { font-weight: bold; }
        """)

class Sidebar(QWidget):
    def __init__(self, items, on_click=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #13293d;")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.header = QLabel("🚗 Smart Parking")
        self.header.setStyleSheet("color: white; font-size: 18px; font-weight: bold; padding: 16px;")
        self.header.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.header)

        btn_container = QWidget()
        btn_layout = QVBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 10, 0, 0)
        btn_layout.setSpacing(0)
        self.main_layout.addWidget(btn_container)

        self.highlight = QFrame(self)
        self.highlight.setStyleSheet("background-color: #1b98e0; border-radius: 3px;")
        self.anim = QPropertyAnimation(self.highlight, b"geometry")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.InOutCubic)

        self.buttons = []
        self._button_texts = items
        for i, item_text in enumerate(items):
            btn = SidebarButton(item_text)
            btn.clicked.connect(lambda checked, b=btn, i=i: (
                self.set_active_button(b), on_click(i) if on_click else None
            ))
            btn_layout.addWidget(btn)
            self.buttons.append(btn)

        btn_layout.addStretch(1)
        self.footer = QLabel("⚙️ Cài đặt | ⏻ Thoát")
        self.footer.setStyleSheet("color: gray; font-size: 13px; padding: 10px;")
        self.footer.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.footer)

        if self.buttons: self.set_active_button(self.buttons[0])

    def set_active_button(self, active_btn):
        for btn in self.buttons: btn.setChecked(False)
        active_btn.setChecked(True)
        y = active_btn.mapTo(self, active_btn.rect().topLeft()).y()
        self.anim.stop()
        self.anim.setStartValue(self.highlight.geometry())
        self.anim.setEndValue(QRect(0, y, 6, active_btn.height()))
        self.anim.start()

    def update_content_visibility(self, is_expanded):
        """Hàm quan trọng: Ẩn/hiện nội dung text để tránh bị tràn."""
        self.header.setVisible(is_expanded)
        self.footer.setVisible(is_expanded)
        for i, btn in enumerate(self.buttons):
            btn.setText(self._button_texts[i] if is_expanded else "")
        self.highlight.setVisible(is_expanded)

class ParkingDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Parking Dashboard")

        self.SIDEBAR_EXPANDED_WIDTH = 180
        self.SIDEBAR_COLLAPSED_WIDTH = 0
        self.sidebar_is_expanded = True

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = Sidebar(["Soát vé", "Thống kê", "Giám sát", "Tra cứu"], self.handle_sidebar_click)
        self.sidebar.setFixedWidth(self.SIDEBAR_EXPANDED_WIDTH)
        main_layout.addWidget(self.sidebar)

        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(10, 5, 10, 10)
        content_layout.setSpacing(10)
        main_layout.addWidget(content_area)

        self.toggle_button = QPushButton("❮")
        self.toggle_button.setFixedSize(25, 25)
        self.toggle_button.setCursor(Qt.PointingHandCursor)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                font-size: 16px; color: white; border: none;
                background-color: #13293d; border-radius: 12px;
            }
            QPushButton:hover { background-color: #1b98e0; }
        """)
        self.toggle_button.clicked.connect(self.toggle_sidebar)

        self.pages = QStackedWidget()
        self.soatve_page = SoatVePage()
        self.thongke_page = StatsPage()
        self.giamsat_page = CameraPage()
        self.tracuu_page = TraCuuPage()
        self.pages.addWidget(self.soatve_page)
        self.pages.addWidget(self.thongke_page)
        self.pages.addWidget(self.giamsat_page)
        self.pages.addWidget(self.tracuu_page)
        
        header_bar = QHBoxLayout()
        header_bar.addWidget(self.toggle_button)
        header_bar.addStretch()
        content_layout.addLayout(header_bar)
        content_layout.addWidget(self.pages)

        # ✨ SỬA LỖI: Animate thuộc tính "minimumWidth"
        self.animation = QPropertyAnimation(self.sidebar, b"minimumWidth")
        self.animation.setDuration(250)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        
        # ✨ KẾT NỐI SIGNAL: Cập nhật lại maximumWidth sau khi animation kết thúc
        self.animation.finished.connect(self.on_animation_finished)

        self.pages.setCurrentIndex(0)
        self.sidebar.buttons[0].click()

    def toggle_sidebar(self):
        if self.sidebar_is_expanded:
            end_width = self.SIDEBAR_COLLAPSED_WIDTH
            self.toggle_button.setText("❯")
            self.sidebar.update_content_visibility(False) # Ẩn nội dung
        else:
            end_width = self.SIDEBAR_EXPANDED_WIDTH
            self.toggle_button.setText("❮")
            self.sidebar.update_content_visibility(True) # Hiện nội dung

        self.animation.setStartValue(self.sidebar.width())
        self.animation.setEndValue(end_width)
        self.animation.start()
        self.sidebar_is_expanded = not self.sidebar_is_expanded

    def on_animation_finished(self):
        """Hàm này đảm bảo layout ổn định sau khi animation chạy xong."""
        width = self.SIDEBAR_EXPANDED_WIDTH if self.sidebar_is_expanded else self.SIDEBAR_COLLAPSED_WIDTH
        self.sidebar.setFixedWidth(width) # Đặt lại fixedWidth để layout không bị "nhảy"

    def handle_sidebar_click(self, index):
        self.pages.setCurrentIndex(index)

    def create_page(self, text):
        page = QWidget()
        layout = QVBoxLayout(page)
        label = QLabel(text, alignment=Qt.AlignCenter)
        label.setFont(QFont("Arial", 16, QFont.Bold))
        layout.addWidget(label)
        return page

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = ParkingDashboard()
    win.show()
    sys.exit(app.exec())