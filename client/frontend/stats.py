# stats_dashboard.py
# -*- coding: utf-8 -*-
"""
Thống kê bãi đỗ xe PySide6 + Matplotlib
Phiên bản UI Standalone: Chỉ hiển thị giao diện, không kết nối database/server.
"""

import sys, math, datetime as dt
from typing import Optional

import numpy as np
import pandas as pd

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QComboBox, QPushButton, QDateEdit, QMessageBox
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ---------------- THEME & CONFIG ----------------
C_DARK   = "#13293d"
C_BG     = "#006494"
C_CARD   = "#247ba0"
C_HILITE = "#1b98e0"
C_LIGHT  = "#e8f1f2"

PARKING_CAPACITY = 200

# ----------------- UI building blocks -----------------------
class Card(QFrame):
    def __init__(self, title: Optional[str] = None, bg=C_CARD, radius=14, padding=12, title_bg=C_DARK):
        super().__init__()
        self.setObjectName("Card")
        self.setStyleSheet(f"""
            QFrame#Card {{
                background-color: {bg};
                border-radius: {radius}px;
            }}
        """)
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
            t.setFont(QFont("Inter, Arial", 14, QFont.Bold))
            tl.addWidget(t)
            self.v.addWidget(tb)

class KPI(QFrame):
    def __init__(self, label, value, sub=None):
        super().__init__()
        self.setStyleSheet(f"background-color:{C_HILITE}; border-radius:12px;")
        v = QVBoxLayout(self)
        v.setContentsMargins(12,12,12,12)
        t = QLabel(label); t.setStyleSheet("color:white;")
        t.setFont(QFont("Inter, Arial", 11))
        self.vv = QLabel(value); self.vv.setStyleSheet("color:white;")
        self.vv.setFont(QFont("Inter, Arial", 22, QFont.Black))
        v.addWidget(t); v.addWidget(self.vv)
        self.ss = QLabel(sub or ""); self.ss.setStyleSheet(f"color:{C_LIGHT};")
        self.ss.setFont(QFont("Inter, Arial", 10))
        v.addWidget(self.ss)
        v.addStretch(1)
    def set(self, value, sub=""):
        self.vv.setText(value); self.ss.setText(sub)

class MplFigure(FigureCanvas):
    def __init__(self, w=5, h=2.8):
        self.fig = Figure(figsize=(w, h), dpi=100)
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.fig.tight_layout()

# ----------------- Main Stats Page -----------------------
class StatsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor(C_BG))
        self.setPalette(pal)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Header / Filters
        header = QHBoxLayout()
        title = QLabel("Thống kê")
        title.setFont(QFont("Inter, Arial", 22, QFont.Black))
        title.setStyleSheet("color:white;")
        header.addWidget(title)
        header.addStretch(1)

        self.rangeBox = QComboBox()
        self.rangeBox.addItems(["7 ngày qua", "30 ngày qua", "Tháng này", "Tùy chỉnh"])
        self.rangeBox.currentTextChanged.connect(self._on_range_change)
        self.rangeBox.setStyleSheet("color:white; background-color:#0f548c; border:0; padding:6px;")
        header.addWidget(self.rangeBox)

        self.fromDate = QDateEdit(); self.toDate = QDateEdit()
        for d in (self.fromDate, self.toDate):
            d.setCalendarPopup(True)
            d.setDate(QDate.currentDate().addDays(-30))
            d.setStyleSheet("color:white; background-color:#0f548c; border:0; padding:6px;")
            d.setVisible(False)
        header.addWidget(self.fromDate); header.addWidget(self.toDate)

        self.btnSim = QPushButton("Simulate Data")
        self.btnSim.setStyleSheet(f"background-color:{C_HILITE}; color:white; border:0; padding:8px 12px; border-radius:8px;")
        self.btnSim.clicked.connect(self._simulate)
        header.addWidget(self.btnSim)
        root.addLayout(header)

        # KPI grid
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(10)
        self.kpi_fill   = KPI("Tỷ lệ lấp đầy", "N/A")
        self.kpi_rev    = KPI("Doanh thu", "N/A")
        self.kpi_active = KPI("Vé đang hoạt động", "N/A")
        self.kpi_dwell  = KPI("Thời gian gửi TB", "N/A")
        for i, k in enumerate([self.kpi_fill, self.kpi_rev, self.kpi_active, self.kpi_dwell]):
            kpi_grid.addWidget(k, 0, i)
        root.addLayout(kpi_grid)

        # Charts row
        charts = QGridLayout(); charts.setSpacing(10)
        self.line_card = Card("Lượt vào/ra theo ngày", bg=C_CARD)
        self.line_fig = MplFigure(w=6.2, h=2.7)
        self.line_card.v.addWidget(self.line_fig)
        charts.addWidget(self.line_card, 0, 0, 1, 2)

        self.rev_card = Card("Doanh thu theo ngày", bg=C_CARD)
        self.rev_fig = MplFigure(w=4.0, h=2.7)
        self.rev_card.v.addWidget(self.rev_fig)
        charts.addWidget(self.rev_card, 0, 2, 1, 1)

        self.heat_card = Card("Mật độ theo giờ x ngày", bg=C_CARD)
        self.heat_fig = MplFigure(w=6.2, h=2.7)
        self.heat_card.v.addWidget(self.heat_fig)
        charts.addWidget(self.heat_card, 1, 0, 1, 2)

        right_col = QVBoxLayout()
        self.status_card = Card("Tình trạng vé", bg=C_CARD)
        self.lbl_status = QLabel("Chưa có dữ liệu")
        self.lbl_status.setStyleSheet(f"color:white;")
        self.status_card.v.addWidget(self.lbl_status)
        right_col.addWidget(self.status_card)

        self.alert_card = Card("Cảnh báo & Dự báo", bg=C_CARD)
        self.lbl_alerts = QLabel("Chưa có dữ liệu")
        self.lbl_alerts.setStyleSheet(f"color:white;")
        self.alert_card.v.addWidget(self.lbl_alerts)
        right_col.addWidget(self.alert_card)
        charts.addLayout(right_col, 1, 2, 1, 1)
        root.addLayout(charts)

        # Không tự động load dữ liệu khi khởi động
        # self._on_range_change(self.rangeBox.currentText())
        self.clear_all_plots()

    def clear_all_plots(self):
        """Xóa trắng tất cả biểu đồ và hiển thị thông báo."""
        for fig in [self.line_fig, self.rev_fig, self.heat_fig]:
            ax = fig.ax
            ax.clear()
            ax.set_title("Chưa có dữ liệu", color="white")
            fig.fig.patch.set_alpha(0)
            ax.set_facecolor('#1b82bf')
            fig.draw()

    def refresh(self):
        """Hàm này sẽ được dùng để load dữ liệu từ API sau này."""
        QMessageBox.information(self, "Thông báo", "Chức năng làm mới dữ liệu sẽ kết nối với server.")
        self.clear_all_plots()

    # ----------------- UI events -----------------------
    def _on_range_change(self, text):
        self.fromDate.setVisible(text == "Tùy chỉnh")
        self.toDate.setVisible(text == "Tùy chỉnh")
        # Gọi refresh để hiển thị thông báo, thay vì load dữ liệu thật
        self.refresh()

    def _simulate(self):
        """Hiển thị thông báo thay vì chạy mô phỏng."""
        QMessageBox.information(self, "Thông báo", "Chức năng mô phỏng dữ liệu được thực hiện ở phía server.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = StatsPage()
    w.setWindowTitle("Thống kê – SmartParking")
    w.resize(1280, 800)
    w.show()
    sys.exit(app.exec())
