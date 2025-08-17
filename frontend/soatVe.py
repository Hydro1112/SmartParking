# parking_dashboard_qt.py
# from logging import root
import sys
from typing import Optional
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFrame, QProgressBar, QTableWidget, QTableWidgetItem, QPushButton,
    QFileDialog, QSizePolicy, QAbstractItemView
)
from PySide6.QtGui import QFont, QColor, QPalette, QPixmap
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
# from sidebar_widget import Sidebar
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


class PieChart(FigureCanvas):
    def __init__(self, data, labels, colors):
        fig = Figure(figsize=(2.8, 2.8), dpi=100)
        super().__init__(fig)
        ax = fig.add_subplot(111)
        ax.pie(
            data, labels=None, autopct='%1.0f%%', startangle=90,
            colors=colors, pctdistance=0.7, textprops={'color': 'white', 'fontsize': 12}
        )
        ax.axis('equal')
        fig.tight_layout()


class LegendDot(QFrame):
    def __init__(self, text, color):
        super().__init__()
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        swatch = QFrame()
        swatch.setFixedSize(16, 16)
        swatch.setStyleSheet(f"background-color:{color}; border-radius:4px;")
        lbl = QLabel(text)
        lbl.setStyleSheet("color: white;")
        lbl.setFont(QFont("Inter, Arial", 12))
        h.addWidget(swatch)
        h.addSpacing(8)
        h.addWidget(lbl)
        h.addStretch(1)


class VideoCard(Card):
    def __init__(self, title: Optional[str] = None, bg=C_CARD):
        super().__init__(title=title, bg=bg)
        self.video = QVideoWidget()
        self.video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.v.addWidget(self.video)

        controls = QHBoxLayout()
        self.btnLoad = QPushButton("Chọn video…")
        self.btnLoad.setStyleSheet(f'''
            QPushButton {{
                background-color: {C_HILITE};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{ opacity: 0.95; }}
        ''')
        controls.addWidget(self.btnLoad, 0, Qt.AlignLeft)
        controls.addStretch(1)
        self.v.addLayout(controls)

        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video)
        self.player.mediaStatusChanged.connect(self._handle_media_status)

        self.btnLoad.clicked.connect(self._choose_file)

    def _choose_file(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "Chọn video demo", "", "Video (*.mp4 *.avi *.mov *.mkv)"
        )
        if f:
            self.player.setSource(QUrl.fromLocalFile(f))
            self.player.play()

    def _handle_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.setPosition(0)
            self.player.play()


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

        # sidebar = Sidebar(["Soát vé", "Thống kê", "Giám sát", "Dữ liệu"], self.handle_sidebar_click, parent=self)
        # root_layout.addWidget(sidebar)

        # Main content
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

        # Row 1: camera - progress+pie - camera
        cam_left  = VideoCard(bg=C_CARD)
        cam_right = VideoCard(bg=C_CARD)
        cam_left.setMinimumHeight(250)
        cam_right.setMinimumHeight(250)

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

        grid.addWidget(cam_left,  0, 0, 1, 1)
        grid.addWidget(mid,       0, 1, 1, 2)
        grid.addWidget(cam_right, 0, 3, 1, 1)

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
        root_layout.addWidget(main, 1)


    # def handle_sidebar_click(self):
    #     # TODO: viết xử lý khi click menu
    #     btn = self.sender()
    #     print(f"Bạn vừa chọn: {btn.text()}")


# if __name__ == "__main__":
#     app = QApplication(sys.argv)
#     win = ParkingDashboard()
#     win.show()
#     sys.exit(app.exec())
    