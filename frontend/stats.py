# stats_dashboard.py
# -*- coding: utf-8 -*-
"""
Thống kê bãi đỗ xe PySide6 + Matplotlib + SQLite
- KPI cards (Lấp đầy, Doanh thu, Vé đang hoạt động, Thời gian gửi TB)
- Biểu đồ lượt vào/ra (30 ngày)
- Biểu đồ doanh thu theo ngày
- Heatmap lưu lượng theo giờ x ngày
- Tỷ lệ loại vé, tình trạng vé
- Cảnh báo rủi ro & Dự báo 7 ngày (SMA)
- Bộ lọc nhanh + Simulate Data
"""

import sys, math, os, random, sqlite3, datetime as dt
from dataclasses import dataclass
from typing import Optional, List, Tuple

import numpy as np
import pandas as pd

from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QFrame, QComboBox, QPushButton, QDateEdit, QTableWidget, QTableWidgetItem,
    QSizePolicy, QSpacerItem
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# ---------------- THEME ----------------
C_DARK   = "#13293d"   # sidebar / header / text dark
C_BG     = "#006494"   # main background
C_CARD   = "#247ba0"   # standard card
C_HILITE = "#1b98e0"   # highlight card
C_LIGHT  = "#e8f1f2"   # light text/lines

DB_PATH = "parking.db"
PARKING_CAPACITY = 200  # sức chứa bãi (config)

# ----------------- Helpers -----------------------
def ensure_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tickets(
        id TEXT PRIMARY KEY,
        plate TEXT,
        vehicle_type TEXT,   -- motor/car
        ticket_type TEXT,    -- hourly/overnight/monthly
        entry_time TEXT,     -- ISO
        exit_time  TEXT,     -- ISO or NULL
        amount REAL DEFAULT 0,
        status TEXT          -- active/closed/cancelled
    )
    """)
    con.commit()
    con.close()

def df_query(sql: str, params=()):
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(sql, con, params=params, parse_dates=["entry_time","exit_time"])
    con.close()
    return df

def execute(sql: str, params=()):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(sql, params)
    con.commit()
    con.close()

def bulk_execute(cmds: List[Tuple[str, tuple]]):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    for sql, p in cmds:
        cur.execute(sql, p)
    con.commit()
    con.close()

def random_plate():
    return f"{random.randint(11, 99)}-{random.choice(['A','B','C','D','G'])}{random.randint(100,999)}.{random.randint(10,99)}"

def price_rule(minutes: int, ticket_type: str, vehicle_type: str) -> float:
    """Giá vé rất đơn giản để demo, bạn có thể thay bằng bảng giá thật."""
    if ticket_type == "monthly":
        return 0.0
    base = 3000 if vehicle_type == "motor" else 10000
    per_hour = 2000 if vehicle_type == "motor" else 5000
    hours = math.ceil(minutes / 60)
    if ticket_type == "overnight":
        return base + per_hour * max(1, hours) + 20000
    return base + per_hour * max(1, hours)

def simulate_days(n_days=35, seed=7):
    random.seed(seed)
    cmds = []
    start = dt.datetime.now().date() - dt.timedelta(days=n_days)
    for i in range(n_days):
        day = start + dt.timedelta(days=i)
        # weekday traffic profile
        base_flow = 120 if day.weekday() < 5 else 80
        noise = random.randint(-20, 20)
        entries = max(30, base_flow + noise)
        for j in range(entries):
            vt = "motor" if random.random() < 0.7 else "car"
            tt = np.random.choice(["hourly","overnight","monthly"], p=[0.7,0.1,0.2])
            et = dt.datetime.combine(day, dt.time(hour=random.randint(6, 21), minute=random.randint(0,59)))
            # monthly: many will not exit the same day (keep active)
            if tt == "monthly" and random.random() < 0.6:
                exit_time = None
                minutes = 0
                amt = 0.0
                status = "active"
            else:
                stay_min = random.randint(20, 6*60)  # 20 min – 6h
                xt = et + dt.timedelta(minutes=stay_min)
                # some roll over to next day
                if random.random() < 0.15: 
                    xt += dt.timedelta(hours=random.randint(2, 18))
                exit_time = xt
                minutes = int((xt - et).total_seconds() / 60)
                amt = price_rule(minutes, tt, vt)
                status = "closed"
            cmds.append((
                "INSERT OR REPLACE INTO tickets(id,plate,vehicle_type,ticket_type,entry_time,exit_time,amount,status) VALUES (?,?,?,?,?,?,?,?)",
                (f"T{day.strftime('%y%m%d')}-{i:02d}-{j:03d}", random_plate(), vt, tt,
                 et.isoformat(sep=' '), 
                 None if exit_time is None else exit_time.isoformat(sep=' '),
                 amt, status)
            ))
    bulk_execute(cmds)

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

        # App background
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
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title.setFont(QFont("Inter, Arial", 22, QFont.Black))
        title.setStyleSheet("color:white;")
        header.addWidget(title)

        header.addStretch(1)

        self.rangeBox = QComboBox()
        self.rangeBox.addItems(["7 ngày qua", "30 ngày qua", "Tháng này", "Tùy chỉnh"])
        self.rangeBox.currentTextChanged.connect(self._on_range_change)
        for w in [self.rangeBox]:
            w.setStyleSheet("color:white; background-color:#0f548c; border:0; padding:6px;")
        header.addWidget(self.rangeBox)

        self.fromDate = QDateEdit(); self.toDate = QDateEdit()
        for d in (self.fromDate, self.toDate):
            d.setCalendarPopup(True)
            d.setDate(QDate.currentDate().addDays(-30))
            d.setStyleSheet("color:white; background-color:#0f548c; border:0; padding:6px;")
            d.setVisible(False)
        header.addWidget(QLabel(" từ ").setStyleSheet if False else QLabel())
        header.addWidget(self.fromDate); header.addWidget(QLabel(" đến ").setStyleSheet if False else QLabel()); header.addWidget(self.toDate)

        self.btnSim = QPushButton("Simulate Data")
        self.btnSim.setStyleSheet(f"background-color:{C_HILITE}; color:white; border:0; padding:8px 12px; border-radius:8px;")
        self.btnSim.clicked.connect(self._simulate)
        header.addWidget(self.btnSim)

        root.addLayout(header)

        # KPI grid
        kpi_grid = QGridLayout()
        kpi_grid.setHorizontalSpacing(10); kpi_grid.setVerticalSpacing(10)
        self.kpi_fill   = KPI("Tỷ lệ lấp đầy", "0%")
        self.kpi_rev    = KPI("Doanh thu (khoảng thời gian)", "0 VND")
        self.kpi_active = KPI("Vé đang hoạt động", "0")
        self.kpi_dwell  = KPI("Thời gian gửi TB", "0 phút")
        for i, k in enumerate([self.kpi_fill, self.kpi_rev, self.kpi_active, self.kpi_dwell]):
            kpi_grid.addWidget(k, 0, i)
        root.addLayout(kpi_grid)

        # Charts row
        charts = QGridLayout(); charts.setHorizontalSpacing(10); charts.setVerticalSpacing(10)
        # Line chart entries/exits
        self.line_card = Card("Lượt vào/ra theo ngày", bg=C_CARD)
        self.line_fig = MplFigure(w=6.2, h=2.7)
        self.line_card.v.addWidget(self.line_fig)
        charts.addWidget(self.line_card, 0, 0, 1, 2)

        # Revenue bar
        self.rev_card = Card("Doanh thu theo ngày", bg=C_CARD)
        self.rev_fig = MplFigure(w=4.0, h=2.7)
        self.rev_card.v.addWidget(self.rev_fig)
        charts.addWidget(self.rev_card, 0, 2, 1, 1)

        # Heatmap
        self.heat_card = Card("Mật độ theo giờ x ngày", bg=C_CARD)
        self.heat_fig = MplFigure(w=6.2, h=2.7)
        self.heat_card.v.addWidget(self.heat_fig)
        charts.addWidget(self.heat_card, 1, 0, 1, 2)

        # Ticket status / alerts
        right_col = QVBoxLayout()
        self.status_card = Card("Tình trạng vé", bg=C_CARD)
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet(f"color:white;")
        self.status_card.v.addWidget(self.lbl_status)
        right_col.addWidget(self.status_card)

        self.alert_card = Card("Cảnh báo & Dự báo 7 ngày", bg=C_CARD)
        self.lbl_alerts = QLabel("")
        self.lbl_alerts.setStyleSheet(f"color:white;")
        self.alert_card.v.addWidget(self.lbl_alerts)
        right_col.addWidget(self.alert_card)

        charts.addLayout(right_col, 1, 2, 1, 1)

        root.addLayout(charts)

        self._on_range_change(self.rangeBox.currentText())

    # ----------------- Data & plots -----------------------
    def _date_range(self):
        today = dt.date.today()
        label = self.rangeBox.currentText()
        if label == "7 ngày qua":
            return today - dt.timedelta(days=6), today
        if label == "30 ngày qua":
            return today - dt.timedelta(days=29), today
        if label == "Tháng này":
            first = today.replace(day=1)
            return first, today
        # Tùy chỉnh
        return self.fromDate.date().toPython(), self.toDate.date().toPython()

    def _load(self):
        d0, d1 = self._date_range()
        # pull tickets intersecting range
        sql = """
        SELECT * FROM tickets
        WHERE DATE(entry_time) <= ? AND (exit_time IS NULL OR DATE(exit_time) >= ?)
        """
        df = df_query(sql, (d1.isoformat(), d0.isoformat()))
        return df, d0, d1

    def _update_kpis(self, df: pd.DataFrame, d0, d1):
        # Occupancy approximation: active tickets on last day vs capacity
        today = d1
        active = df[(df["status"]=="active") | (df["exit_time"].isna())]
        # active at end of range ≈ entries before end and (no exit or exit after end)
        active_at_end = df[(pd.to_datetime(df["entry_time"]).dt.date <= today) &
                           (df["exit_time"].isna() | (pd.to_datetime(df["exit_time"]).dt.date > today))]
        fill_rate = (len(active_at_end) / PARKING_CAPACITY) if PARKING_CAPACITY else 0
        self.kpi_fill.set(f"{fill_rate*100:.0f}%", f"Sức chứa: {PARKING_CAPACITY}")

        # Revenue in range: sum amounts where exit_time within [d0,d1]
        ex = df.dropna(subset=["exit_time"]).copy()
        ex["exit_d"] = pd.to_datetime(ex["exit_time"]).dt.date
        rev = ex[(ex["exit_d"]>=d0) & (ex["exit_d"]<=d1)]["amount"].sum()
        self.kpi_rev.set(f"{int(rev):,} VND".replace(",", "."), f"{d0.strftime('%d/%m')}–{d1.strftime('%d/%m')}")

        # Active tickets count
        self.kpi_active.set(str(len(active_at_end)), "Vé đang lưu xe")

        # Avg dwell time (closed tickets in range)
        if not ex.empty:
            ex["minutes"] = (pd.to_datetime(ex["exit_time"]) - pd.to_datetime(ex["entry_time"])).dt.total_seconds()/60
            mins = ex["minutes"].mean()
            self.kpi_dwell.set(f"{mins:.0f} phút", "Trung bình vé đã đóng")
        else:
            self.kpi_dwell.set("0 phút", "")

    def _plot_lines(self, df: pd.DataFrame, d0, d1):
        ax = self.line_fig.ax; ax.clear()
        days = pd.date_range(d0, d1, freq="D")
        # entries by day
        e = pd.to_datetime(df["entry_time"]).dt.date.value_counts().sort_index()
        x_in = [e.get(d.date(), 0) for d in days]
        # exits by day
        exits = pd.to_datetime(df["exit_time"]).dropna().dt.date.value_counts().sort_index()
        x_out = [exits.get(d.date(), 0) for d in days]
        ax.plot(days, x_in, label="Vào")
        ax.plot(days, x_out, label="Ra")
        ax.set_title("Lượt xe theo ngày", color="white")
        ax.set_ylabel("Số lượt", color="white")
        ax.tick_params(axis='x', labelrotation=0, labelsize=8, colors="white")
        ax.tick_params(axis='y', colors="white")
        ax.legend(facecolor='#0f548c', edgecolor='none', labelcolor='white')
        self.line_fig.fig.patch.set_alpha(0)
        ax.set_facecolor('#1b82bf')
        self.line_fig.draw()

        # Forecast 7d (SMA)
        series = pd.Series(x_in, index=days)
        sma = series.rolling(7, min_periods=3).mean().iloc[-1]
        if not np.isnan(sma):
            future_x = pd.date_range(d1 + dt.timedelta(days=1), d1 + dt.timedelta(days=7))
            ax.plot(future_x, [sma]*7, linestyle="--", label="Dự báo SMA")
            ax.legend(facecolor='#0f548c', edgecolor='none', labelcolor='white')
            self.line_fig.draw()

        # Alerts text
        last7 = series.tail(7).mean() if len(series)>=7 else series.mean()
        prev7 = series.shift(7).tail(7).mean() if len(series)>=14 else last7
        trend = ((last7 - prev7) / prev7 * 100) if prev7 else 0
        msg = f"Xu hướng 7 ngày: {'tăng' if trend>=0 else 'giảm'} {abs(trend):.1f}% so với 7 ngày trước."
        self.lbl_alerts.setText(f"<p style='color:white'>{msg}</p>" + (self.lbl_alerts.text() or ""))

    def _plot_revenue(self, df: pd.DataFrame, d0, d1):
        ax = self.rev_fig.ax; ax.clear()
        closed = df.dropna(subset=["exit_time"]).copy()
        if closed.empty:
            ax.set_title("Chưa có doanh thu", color="white"); self.rev_fig.draw(); return
        closed["exit_d"] = pd.to_datetime(closed["exit_time"]).dt.date
        g = closed.groupby("exit_d")["amount"].sum()
        xs = pd.date_range(d0, d1, freq="D")
        ys = [g.get(d.date(), 0) for d in xs]
        ax.bar(xs, ys)
        ax.set_title("Doanh thu theo ngày", color="white")
        ax.tick_params(axis='x', labelrotation=0, labelsize=8, colors="white")
        ax.tick_params(axis='y', colors="white")
        self.rev_fig.fig.patch.set_alpha(0)
        ax.set_facecolor('#1b82bf')
        self.rev_fig.draw()

    def _plot_heat(self, df: pd.DataFrame, d0, d1):
        ax = self.heat_fig.ax; ax.clear()
        if df.empty:
            ax.set_title("Chưa có dữ liệu", color="white"); self.heat_fig.draw(); return
        dfe = df.copy()
        dfe["d"] = pd.to_datetime(dfe["entry_time"])
        dfe["day"] = dfe["d"].dt.date
        dfe["hour"] = dfe["d"].dt.hour
        xs = pd.date_range(d0, d1, freq="D")
        mat = np.zeros((24, len(xs)))
        vc = dfe.groupby(["hour","day"])["id"].count()
        for c, day in enumerate(xs.date):
            for h in range(24):
                mat[h, c] = vc.get((h, day), 0)
        im = ax.imshow(mat, aspect='auto', origin='lower')
        ax.set_yticks([0,6,12,18,23]); ax.set_yticklabels(["0h","6h","12h","18h","23h"], color="white")
        ax.set_xticks(range(len(xs))); 
        ax.set_xticklabels([d.strftime("%d/%m") for d in xs], rotation=90, fontsize=7, color="white")
        ax.set_title("Mật độ theo giờ (đếm lượt vào)", color="white")
        self.heat_fig.fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
        self.heat_fig.fig.patch.set_alpha(0)
        ax.set_facecolor('#1b82bf')
        self.heat_fig.draw()

    def _ticket_status(self, df: pd.DataFrame, d0, d1):
        total = len(df)
        active = ((df["status"]=="active") | df["exit_time"].isna()).sum()
        closed = ((df["status"]=="closed") & df["exit_time"].notna()).sum()
        cancelled = (df["status"]=="cancelled").sum()
        monthly = (df["ticket_type"]=="monthly").sum()
        hourly  = (df["ticket_type"]=="hourly").sum()
        overnight = (df["ticket_type"]=="overnight").sum()
        html = f"""
        <div style='color:white'>
            Tổng vé trong khoảng: <b>{total}</b><br>
            Đang hoạt động: <b>{active}</b> &nbsp;|&nbsp; Đã đóng: <b>{closed}</b> &nbsp;|&nbsp; Hủy: <b>{cancelled}</b><br>
            Loại vé – Giờ: <b>{hourly}</b>, Qua đêm: <b>{overnight}</b>, Tháng: <b>{monthly}</b>
        </div>
        """
        self.lbl_status.setText(html)

        # Rủi ro rule-based
        alerts = []
        if PARKING_CAPACITY and active > 0.9 * PARKING_CAPACITY:
            alerts.append("⚠️ Gần đầy bãi (>90% sức chứa).")
        if cancelled > 0:
            alerts.append(f"⚠️ Có {cancelled} vé bị hủy trong khoảng thời gian.")
        if not alerts:
            alerts.append("✅ Không có rủi ro đáng chú ý.")
        self.lbl_alerts.setText("<br>".join([f"<span style='color:white'>{a}</span>" for a in alerts]))

    def refresh(self):
        df, d0, d1 = self._load()
        self._update_kpis(df, d0, d1)
        self._plot_lines(df, d0, d1)
        self._plot_revenue(df, d0, d1)
        self._plot_heat(df, d0, d1)
        self._ticket_status(df, d0, d1)

    # ----------------- UI events -----------------------
    def _on_range_change(self, text):
        custom = text == "Tùy chỉnh"
        self.fromDate.setVisible(custom); self.toDate.setVisible(custom)
        if not custom:
            # set sensible defaults for internal state
            if text == "7 ngày qua":
                self.fromDate.setDate(QDate.currentDate().addDays(-6))
                self.toDate.setDate(QDate.currentDate())
            elif text == "30 ngày qua":
                self.fromDate.setDate(QDate.currentDate().addDays(-29))
                self.toDate.setDate(QDate.currentDate())
            elif text == "Tháng này":
                first = QDate.currentDate().addDays(1 - QDate.currentDate().day())
                self.fromDate.setDate(first); self.toDate.setDate(QDate.currentDate())
        self.refresh()

    def _simulate(self):
        simulate_days(n_days=40, seed=random.randint(1,9999))
        self.refresh()

# ----------------- App -----------------------
# def main():
#     ensure_db()
#     # auto seed once if DB empty
#     con = sqlite3.connect(DB_PATH); cur = con.cursor()
#     cur.execute("SELECT COUNT(*) FROM tickets"); n = cur.fetchone()[0]; con.close()
#     if n == 0:
#         simulate_days(35)

#     app = QApplication(sys.argv)
#     w = StatsPage()
#     w.setWindowTitle("Thống kê – SmartParking")
#     w.resize(1280, 800)
#     w.show()
#     sys.exit(app.exec())

# if __name__ == "__main__":
#     main()
