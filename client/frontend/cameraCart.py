# FILE: client/frontend/cameraCart.py (ĐÃ SỬA LỖI KÍCH THƯỚC)

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QPushButton, QGridLayout, QSplitter, QApplication, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

# ==== COLORS ====
C_DARK     = "#13293d"
C_HEADER   = "#0d1b2a"
C_SIDEBAR  = "#1b263b"
C_BG       = "#006494"
C_CARD     = "#247ba0"
C_HILITE   = "#1b98e0"
C_LIGHT    = "#e8f1f2"

class CameraCard(QFrame):
    def __init__(self, name, alert=False):
        super().__init__()
        self.setObjectName("CameraCard")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # video placeholder
        self.video = QLabel("VIDEO")
        self.video.setStyleSheet("background-color: black; border-radius:8px; color:white;")
        
        # ✨ THAY ĐỔI QUAN TRỌNG: Bỏ kích thước cố định, cho phép co giãn
        # self.video.setFixedSize(500, 300) # <-- XÓA DÒNG NÀY
        self.video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video.setMinimumSize(320, 180) # Đặt kích thước tối thiểu hợp lý
        
        self.video.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.video)

        # camera label
        label = QLabel(name)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"color:{C_LIGHT}; font-size:12px; padding:2px; min-height:20px; max-height:20px;")
        layout.addWidget(label)

        self.setLayout(layout)
        self.setStyleSheet(f"""
            QFrame#CameraCard {{
                background-color: {C_CARD};
                border-radius: 12px;
                border: 2px solid {"red" if alert else C_CARD};
                margin: 2px;
            }}
        """)

class CameraPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color:{C_BG};") # Đặt màu nền chung

        # ==== HEADER ====
        header = QHBoxLayout()
        header.setContentsMargins(20, 4, 20, 4)
        header.setSpacing(12)

        title = QLabel("Giám sát bãi đỗ xe")
        title.setStyleSheet(f"color:{C_LIGHT}; font-size:16px; font-weight:bold;")
        header.addWidget(title)
        header.addStretch()

        for icon in ["search", "view-fullscreen", "list-add", "settings"]:
            btn = QPushButton()
            btn.setIcon(QIcon.fromTheme(icon))
            btn.setFixedSize(28, 28)
            btn.setStyleSheet("border:none; color:white;")
            header.addWidget(btn)

        headerWidget = QWidget()
        headerWidget.setLayout(header)
        headerWidget.setFixedHeight(36)
        headerWidget.setStyleSheet(f"background-color:{C_HEADER};")

        # ==== SIDEBAR ====
        sidebar = QVBoxLayout()
        sidebar.setSpacing(16)
        sidebar.setContentsMargins(10, 10, 10, 10)

        area_label = QLabel("Khu vực")
        area_label.setStyleSheet(f"color: {C_LIGHT}; font-size: 20px; font-weight: bold;")
        sidebar.addWidget(area_label)

        areas = ["Cổng chính", "Khu A", "Khu B", "Tầng hầm"]
        for area in areas:
            lbl = QLabel(area)
            lbl.setStyleSheet(f"color: {C_LIGHT}; font-size: 16px;")
            sidebar.addWidget(lbl)
        sidebar.addStretch(1)

        warn_label = QLabel("Cảnh báo")
        warn_label.setStyleSheet(f"color: {C_LIGHT}; font-size: 20px; font-weight: bold; margin-top: 12px;")
        sidebar.addWidget(warn_label)

        warnings = [("Cam 5: Mất tín hiệu", "red"), ("Cam 13: Mất tín hiệu", "red")]
        for text, color in warnings:
            lbl = QLabel(f"● {text}")
            lbl.setStyleSheet(f"color: {color}; font-size: 14px;")
            sidebar.addWidget(lbl)
        sidebar.addStretch(2)

        sidebarWidget = QWidget()
        sidebarWidget.setLayout(sidebar)
        sidebarWidget.setFixedWidth(180)
        sidebarWidget.setStyleSheet(f"background-color: {C_SIDEBAR};")

        # ==== CAMERA GRID ====
        grid = QGridLayout()
        grid.setSpacing(12)
        cams = [
            ("Camera 1 - Cổng chính", False), ("Camera 2 - Khu A", False), ("Camera 3 - Khu A", True),
            ("Camera 4 - Khu B", False), ("Camera 5 - Hầm", True), ("Camera 6 - Khu B", False),
        ]
        for i, (name, alert) in enumerate(cams):
            grid.addWidget(CameraCard(name, alert), i // 3, i % 3)

        gridWidget = QWidget()
        gridWidget.setLayout(grid)

        # ==== SPLITTER ====
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(gridWidget)
        splitter.addWidget(sidebarWidget)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 1)

        # ==== MAIN LAYOUT ====
        mainLayout = QVBoxLayout(self)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)
        mainLayout.addWidget(headerWidget)
        mainLayout.addWidget(splitter)