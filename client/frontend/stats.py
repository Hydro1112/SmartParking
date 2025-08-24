# stats_dashboard.py (PHIÊN BẢN SỬA LỖI HIỂN THỊ CUỐI CÙNG)
# -*- coding: utf-8 -*-
import sys
from datetime import datetime, timedelta
from typing import Optional
import aiohttp
import asyncio

# <<<<< THÊM CÁC IMPORT CẦN THIẾT CHO MATPLOTLIB
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QComboBox, QPushButton, QDateEdit
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# <<<<< ĐÂY LÀ DÒNG LỆNH QUAN TRỌNG NHẤT
# <<<<< Ra lệnh cho Matplotlib sử dụng style nền tối cho TẤT CẢ biểu đồ
plt.style.use('dark_background')

# ---------------- THEME & CONFIG ----------------
C_DARK   = "#13293d"
C_BG     = "#006494"
C_CARD   = "#247ba0"
C_HILITE = "#1b98e0"
C_LIGHT  = "#e8f1f2"
API_URL = "http://localhost:8000/api"

# ----------------- UI building blocks (Không thay đổi) -----------------------
class Card(QFrame):
    def __init__(self, title: Optional[str] = None, bg=C_CARD, radius=14, padding=12, title_bg=C_DARK):
        super().__init__()
        self.setObjectName("Card")
        self.setStyleSheet(f"QFrame#Card {{ background-color: {bg}; border-radius: {radius}px; }}")
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(padding, padding, padding, padding); self.v.setSpacing(10)
        if title:
            tb = QFrame(); tb.setStyleSheet(f"background-color: {title_bg}; border-radius: 10px;")
            tl = QHBoxLayout(tb); tl.setContentsMargins(12, 8, 12, 8)
            t = QLabel(title); t.setStyleSheet("color: white;"); t.setFont(QFont("Inter, Arial", 14, QFont.Bold))
            tl.addWidget(t); self.v.addWidget(tb)

class KPI(QFrame):
    def __init__(self, label, value, sub=None):
        super().__init__()
        self.setStyleSheet(f"background-color:{C_HILITE}; border-radius:12px;")
        v = QVBoxLayout(self); v.setContentsMargins(12,12,12,12)
        t = QLabel(label); t.setStyleSheet("color:white;"); t.setFont(QFont("Inter, Arial", 11))
        self.vv = QLabel(value); self.vv.setStyleSheet("color:white;"); self.vv.setFont(QFont("Inter, Arial", 22, QFont.Black))
        v.addWidget(t); v.addWidget(self.vv)
        self.ss = QLabel(sub or ""); self.ss.setStyleSheet(f"color:{C_LIGHT};"); self.ss.setFont(QFont("Inter, Arial", 10))
        v.addWidget(self.ss); v.addStretch(1)
    def set(self, value, sub=""): self.vv.setText(value); self.ss.setText(sub)

class MplFigure(FigureCanvas):
    def __init__(self, w=5, h=2.8):
        self.fig = Figure(figsize=(w, h), dpi=100)
        super().__init__(self.fig)
        # Nền của Figure (khung bao ngoài) sẽ được style 'dark_background' xử lý
        # Chúng ta sẽ chỉ đặt màu cho vùng vẽ (axes) bên trong cho khớp theme

    def clear_figure(self):
        self.fig.clear()

# ----------------- Main Stats Page -----------------------
class StatsPage(QWidget):
    # Các hàm còn lại giữ nguyên, chỉ tinh chỉnh nhỏ trong hàm style
    def __init__(self):
        super().__init__()
        self.setAutoFillBackground(True)
        pal = self.palette(); pal.setColor(QPalette.Window, QColor(C_BG)); self.setPalette(pal)
        root = QVBoxLayout(self); root.setContentsMargins(12, 12, 12, 12); root.setSpacing(10)
        header = QHBoxLayout()
        title = QLabel("Thống kê"); title.setFont(QFont("Inter, Arial", 22, QFont.Black)); title.setStyleSheet("color:white;")
        header.addWidget(title); header.addStretch(1)
        self.rangeBox = QComboBox(); self.rangeBox.addItems(["Hôm nay", "7 ngày qua", "30 ngày qua", "Tháng này", "Tùy chỉnh"])
        self.rangeBox.currentTextChanged.connect(self.on_range_change)
        self.rangeBox.setStyleSheet("color:white; background-color:#0f548c; border:0; padding:6px;")
        header.addWidget(self.rangeBox)
        self.fromDate = QDateEdit(); self.toDate = QDateEdit()
        for d, days_ago in [(self.fromDate, 6), (self.toDate, 0)]:
            d.setCalendarPopup(True); d.setDate(QDate.currentDate().addDays(-days_ago))
            d.setStyleSheet("color:white; background-color:#0f548c; border:0; padding:6px;")
            d.setVisible(False); d.dateChanged.connect(self.refresh_data)
        header.addWidget(self.fromDate); header.addWidget(self.toDate)
        self.btnRefresh = QPushButton("Làm mới")
        self.btnRefresh.setStyleSheet(f"background-color:{C_HILITE}; color:white; border:0; padding:8px 12px; border-radius:8px;")
        self.btnRefresh.clicked.connect(self.refresh_data); header.addWidget(self.btnRefresh)
        root.addLayout(header)
        kpi_grid = QGridLayout(); kpi_grid.setSpacing(10)
        self.kpi_fill   = KPI("Tỷ lệ lấp đầy", "N/A"); self.kpi_rev    = KPI("Doanh thu", "N/A")
        self.kpi_active = KPI("Vé đang hoạt động", "N/A"); self.kpi_dwell  = KPI("Thời gian gửi TB", "N/A")
        for i, k in enumerate([self.kpi_fill, self.kpi_rev, self.kpi_active, self.kpi_dwell]): kpi_grid.addWidget(k, 0, i)
        root.addLayout(kpi_grid)
        charts = QGridLayout(); charts.setSpacing(10)
        self.line_card = Card("Lượt vào/ra theo ngày", bg=C_CARD); self.line_fig = MplFigure(w=6.2, h=2.7)
        self.line_card.v.addWidget(self.line_fig); charts.addWidget(self.line_card, 0, 0, 1, 2)
        self.rev_card = Card("Doanh thu theo ngày", bg=C_CARD); self.rev_fig = MplFigure(w=4.0, h=2.7)
        self.rev_card.v.addWidget(self.rev_fig); charts.addWidget(self.rev_card, 0, 2, 1, 1)
        self.heat_card = Card("Mật độ xe vào (Giờ x Ngày trong tuần)", bg=C_CARD); self.heat_fig = MplFigure(w=6.2, h=2.7)
        self.heat_card.v.addWidget(self.heat_fig); charts.addWidget(self.heat_card, 1, 0, 1, 2)
        right_col = QVBoxLayout()
        self.status_card = Card("Tình trạng vé", bg=C_CARD)
        self.lbl_status = QLabel("Đang tải..."); self.lbl_status.setStyleSheet(f"color:white;"); self.lbl_status.setWordWrap(True)
        self.status_card.v.addWidget(self.lbl_status); right_col.addWidget(self.status_card)
        self.alert_card = Card("Cảnh báo gần đây", bg=C_CARD)
        self.lbl_alerts = QLabel("Đang tải..."); self.lbl_alerts.setStyleSheet(f"color:white;"); self.lbl_alerts.setWordWrap(True)
        self.alert_card.v.addWidget(self.lbl_alerts); right_col.addWidget(self.alert_card)
        charts.addLayout(right_col, 1, 2, 1, 1); root.addLayout(charts)
    def start_initial_fetch(self): self.on_range_change(self.rangeBox.currentText())
    def on_range_change(self, text):
        is_custom = (text == "Tùy chỉnh")
        self.fromDate.setVisible(is_custom); self.toDate.setVisible(is_custom)
        if not is_custom: self.refresh_data()
    def refresh_data(self): asyncio.create_task(self.fetch_and_update_stats())
    async def fetch_and_update_stats(self):
        now = datetime.now(); selection = self.rangeBox.currentText()
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0); end_date = now
        if selection == "Tùy chỉnh":
            start_dt = self.fromDate.date().toPython(); end_dt = self.toDate.date().toPython()
            start_date = datetime.combine(start_dt, datetime.min.time()); end_date = datetime.combine(end_dt, datetime.max.time())
        elif selection == "Hôm nay": start_date = start_date
        elif selection == "7 ngày qua": start_date = start_date - timedelta(days=6)
        elif selection == "30 ngày qua": start_date = start_date - timedelta(days=29)
        elif selection == "Tháng này": start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_iso = start_date.isoformat(); end_iso = end_date.isoformat()
        try:
            async with aiohttp.ClientSession() as session:
                params = {"start_date": start_iso, "end_date": end_iso}
                async with session.get(f"{API_URL}/stats", params=params) as resp:
                    if resp.status == 200: self.update_ui(await resp.json(), start_date, end_date)
                    else: self.show_error_on_ui()
        except Exception: self.show_error_on_ui()
    def show_error_on_ui(self):
        for k in [self.kpi_fill, self.kpi_rev, self.kpi_active, self.kpi_dwell]: k.set("Lỗi", "Không có dữ liệu")
        for fig_canvas in [self.line_fig, self.rev_fig, self.heat_fig]:
            fig_canvas.clear_figure(); ax = fig_canvas.fig.add_subplot(111)
            ax.set_facecolor(C_CARD); ax.set_title("Lỗi tải dữ liệu", color='red'); fig_canvas.draw()
        self.lbl_status.setText("Không thể tải dữ liệu."); self.lbl_alerts.setText("Không thể tải dữ liệu.")
    def update_ui(self, data, start_date, end_date):
        kpis = data.get('kpis', {}); fill_pct = (kpis['occupancy']['current'] / kpis['occupancy']['capacity']) * 100 if kpis.get('occupancy') and kpis['occupancy']['capacity'] > 0 else 0
        self.kpi_fill.set(f"{fill_pct:.1f}%", f"{kpis.get('occupancy',{}).get('current',0)} / {kpis.get('occupancy',{}).get('capacity',0)}")
        self.kpi_rev.set(f"{kpis.get('revenue', 0):,} đ"); self.kpi_active.set(f"{kpis.get('active_tickets', 0)}")
        dwell_min = kpis.get('avg_dwell_time_minutes', 0) or 0; self.kpi_dwell.set(f"{dwell_min:.0f} phút", f"~ {dwell_min/60:.1f} giờ")
        charts = data.get('charts', {}); date_range_str = f"({start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m/%Y')})"
        self.update_traffic_chart(charts.get('traffic', {}), date_range_str)
        self.update_revenue_chart(charts.get('revenue', {}), date_range_str)
        self.update_heatmap(charts.get('heatmap', []), date_range_str)
        other = data.get('other', {}); status_text = "\n".join([f"• {s['type'].capitalize()} ({s['status']}): {s['count']}" for s in other.get('ticket_status', [])])
        self.lbl_status.setText(status_text or "Không có dữ liệu."); alerts_text = "\n".join([f"• [{a['severity'].upper()}] {a['message']}" for a in other.get('alerts', [])])
        self.lbl_alerts.setText(alerts_text or "Không có cảnh báo.")
    
    def _setup_ax_style(self, ax, title):
        # Dòng này vẫn quan trọng để custom màu nền cho khớp với Card
        ax.set_facecolor(C_CARD) 
        # Các style khác sẽ được 'dark_background' xử lý, nhưng ta có thể ghi đè nếu muốn
        ax.set_title(title, fontsize=12, pad=15)
        ax.tick_params(labelsize=8)
        # Ghi đè màu của các đường viền trục tọa độ cho đẹp hơn
        for spine in ['left', 'bottom']: ax.spines[spine].set_color(C_LIGHT)
        return ax

    def update_traffic_chart(self, data, date_range_str):
        self.line_fig.clear_figure(); ax = self.line_fig.fig.add_subplot(111)
        self._setup_ax_style(ax, f"Lưu lượng xe ra vào\n{date_range_str}")
        if not data or not data.get('dates'):
            ax.text(0.5, 0.5, "Không có dữ liệu", ha='center', va='center'); self.line_fig.draw(); return
        dates = [datetime.strptime(d, '%Y-%m-%d') for d in data['dates']]
        ax.plot(dates, data['in_counts'], label='Lượt vào', color='#34d399', marker='o', linestyle='-')
        ax.plot(dates, data['out_counts'], label='Lượt ra', color='#f87171', marker='o', linestyle='--')
        ax.set_ylabel("Số lượt xe", fontsize=9); ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=5))
        ax.grid(True, linestyle='--', alpha=0.2, axis='y')
        ax.legend(fontsize=8)
        self.line_fig.fig.autofmt_xdate(rotation=20, ha='right'); self.line_fig.fig.tight_layout(pad=1.5); self.line_fig.draw()

    def update_revenue_chart(self, data, date_range_str):
        self.rev_fig.clear_figure(); ax = self.rev_fig.fig.add_subplot(111)
        self._setup_ax_style(ax, f"Doanh thu (nghìn đ)\n{date_range_str}")
        if not data or not data.get('dates'):
            ax.text(0.5, 0.5, "Không có dữ liệu", ha='center', va='center'); self.rev_fig.draw(); return
        dates = [datetime.strptime(d, '%Y-%m-%d') for d in data['dates']]
        amounts = [a / 1000 for a in data['amounts']]; ax.bar(dates, amounts, color=C_HILITE, width=0.6)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:,.0f}k'))
        ax.set_ylabel("Số tiền (x1000 VNĐ)", fontsize=9)
        self.rev_fig.fig.autofmt_xdate(rotation=20, ha='right'); self.rev_fig.fig.tight_layout(pad=1.5); self.rev_fig.draw()

    def update_heatmap(self, data, date_range_str):
        self.heat_fig.clear_figure(); ax = self.heat_fig.fig.add_subplot(111)
        self._setup_ax_style(ax, f"Mật độ xe vào trong tuần\n{date_range_str}")
        if not data or not any(sum(row) for row in data):
            ax.text(0.5, 0.5, "Không có dữ liệu", ha='center', va='center'); self.heat_fig.draw(); return
        im = ax.imshow(data, cmap='viridis', aspect='auto')
        cbar = self.heat_fig.fig.colorbar(im, ax=ax, pad=0.02)
        cbar.set_label('Số lượt xe vào', fontsize=9)
        cbar.locator = mticker.MaxNLocator(integer=True)
        cbar.update_ticks()
        ax.set_xticks(range(0, 24, 2)); ax.set_xticklabels([f'{h}h' for h in range(0, 24, 2)])
        ax.set_xlabel("Giờ trong ngày", fontsize=9)
        ax.set_yticks(range(7)); ax.set_yticklabels(['T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'CN'])
        ax.set_ylabel("Ngày trong tuần", fontsize=9)
        self.heat_fig.fig.tight_layout(pad=1.5); self.heat_fig.draw()

# --- Phần main để chạy độc lập ---
if __name__ == "__main__":
    import qasync
    app = QApplication(sys.argv)
    w = StatsPage(); w.setWindowTitle("Thống kê – SmartParking")
    w.resize(1280, 800); w.show(); w.start_initial_fetch()
    loop = qasync.QEventLoop(app); asyncio.set_event_loop(loop)
    with loop: loop.run_forever()