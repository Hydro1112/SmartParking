import sys
import asyncio
import json
import cv2
import base64
import websockets
import aiohttp
import numpy as np
import time
import traceback
from datetime import datetime

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap

from frontend.home import ParkingDashboard

# ==================== CONFIG ====================
SERVER_URL = "ws://localhost:8000/ws/camera"
API_URL = "http://localhost:8000/api"
FRONTEND_ONLY = False
RECONNECT_DELAY = 5
# ================================================

class App(ParkingDashboard):
    def __init__(self):
        super().__init__()
        self.video_label_in = self.soatve_page.mid_cam_in.video
        self.video_label_out = self.soatve_page.mid_cam_out.video
        self.frame_in, self.frame_out = None, None
        self.popup_shown_for_plate = {}; self.popup_cooldown = 15; self.active_popups = set()
        self.timer = QTimer(); self.timer.timeout.connect(self.update_frames); self.timer.start(30)

    async def start(self):
        await self.update_status_cards(); await self.populate_initial_history()
        await asyncio.gather(self.run_camera(0, "in"), self.run_camera(1, "out"))

    def _unwrap_history_data(self, data):
        if not data or not data.get("vehicle") or not data.get("history"): return None
        v, h, t = data.get("vehicle",{}), data.get("history",{}), data.get("ticket",{})
        et = h.get("event_type")
        time_iso = t.get("checkin_time") if et == "in" else t.get("checkout_time")
        time_str = "---"
        if time_iso:
            try: time_str = datetime.fromisoformat(time_iso).strftime('%H:%M:%S %d/%m/%Y')
            except: pass
        return {"plate": v.get("plate"), "vehicle_type": v.get("vehicle_type"), "license_plate_image": v.get("license_plate_image"), "ticket_type": t.get("ticket_type", "N/A"), "time": time_str, "event_type": et}

    async def populate_initial_history(self):
        print("[CLIENT] 📜 Đang điền dữ liệu lịch sử ban đầu...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_URL}/history/recent?limit=10") as resp:
                    if resp.status != 200: print(f"Lỗi khi lấy lịch sử ban đầu: {resp.status}"); return
                    for event_data in reversed(await resp.json()):
                        unwrapped_event = self._unwrap_history_data(event_data)
                        if unwrapped_event: self.soatve_page.add_to_history(unwrapped_event)
        except Exception as e: print(f"[CLIENT] ⚠️ Lỗi khi điền lịch sử ban đầu: {e}")

    async def handle_new_event(self, event_type: str):
        print(f"[CLIENT] ✨ Xử lý sự kiện mới: '{event_type}'")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_URL}/history/latest") as resp:
                    if resp.status != 200: print(f"Lỗi lấy lịch sử: {resp.status}"); return
                    history_data = await resp.json()
                    latest_in = self._unwrap_history_data(history_data.get("latest_in"))
                    latest_out = self._unwrap_history_data(history_data.get("latest_out"))
                    self.soatve_page.update_cards(latest_in, latest_out)
                    if event_type == "in" and latest_in: self.soatve_page.add_to_history(latest_in)
                    elif event_type == "out" and latest_out: self.soatve_page.add_to_history(latest_out)
        except Exception as e: print(f"[CLIENT] ⚠️ Lỗi khi xử lý sự kiện mới: {e}"); traceback.print_exc()

    async def update_status_cards(self):
        print("[CLIENT] 🔄 Cập nhật card trạng thái...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_URL}/history/latest") as resp:
                    if resp.status == 200:
                        history_data = await resp.json()
                        latest_in = self._unwrap_history_data(history_data.get("latest_in"))
                        latest_out = self._unwrap_history_data(history_data.get("latest_out"))
                        self.soatve_page.update_cards(latest_in, latest_out)
        except Exception as e: print(f"[CLIENT] ⚠️ Lỗi khi cập nhật card trạng thái: {e}")

    async def choose_ticket(self, car_id, plate, vehicle_type, ticket_type, vehicle_image_b64):
        payload = { "car_id": str(car_id), "plate": str(plate), "vehicle_type": str(vehicle_type), "ticket_type": str(ticket_type), "vehicle_image_b64": vehicle_image_b64 }
        try:
            async with aiohttp.ClientSession() as session, session.post(f"{API_URL}/ticket/choose", json=payload) as resp:
                if resp.status == 200: print(f"[CLIENT] ✅ Đã gửi lựa chọn vé: {plate}"); await self.handle_new_event("in")
                else: print(f"[CLIENT] ❌ Gửi lựa chọn vé thất bại: {resp.status} - {await resp.text()}")
        except Exception as e: print(f"[CLIENT] ⚠️ Lỗi khi gửi yêu cầu tạo vé: {e}")

    async def confirm_checkout(self, plate: str):
        try:
            async with aiohttp.ClientSession() as session, session.post(f"{API_URL}/ticket/checkout", json={"plate": plate}) as resp:
                if resp.status == 200: print(f"[CLIENT] ✅ Đã xác nhận checkout: {plate}"); await self.handle_new_event("out")
                else: print(f"[CLIENT] ❌ Xác nhận checkout thất bại: {resp.status} - {await resp.text()}")
        except Exception as e: print(f"[CLIENT] ⚠️ Lỗi khi yêu cầu checkout: {e}")

    async def log_monthly_checkin(self, plate: str):
        try:
            async with aiohttp.ClientSession() as session, session.post(f"{API_URL}/ticket/log_entry", json={"plate": plate}) as resp:
                if resp.status == 200: print(f"[CLIENT] ✅ Đã ghi nhận xe vé tháng vào: {plate}"); await self.handle_new_event("in")
                else: print(f"[CLIENT] ❌ Ghi nhận xe vé tháng thất bại: {resp.status} - {await resp.text()}")
        except Exception as e: print(f"[CLIENT] ⚠️ Lỗi khi ghi nhận xe vé tháng: {e}")

    async def run_camera(self, cam_id: int, which: str):
        cap = cv2.VideoCapture(cam_id)
        if not cap.isOpened(): print(f"[CLIENT] ❌ Không thể mở webcam {cam_id}"); return
        print(f"[CLIENT] ✅ Đã mở webcam {cam_id}")
        if FRONTEND_ONLY: return
        url = f"{SERVER_URL}/{cam_id}"
        while True:
            try:
                async with websockets.connect(url) as ws:
                    print(f"[CLIENT] 🔗 Đã kết nối camera {cam_id}")
                    while True:
                        ret, frame = cap.read();
                        if not ret: continue
                        ok, buf = cv2.imencode(".jpg", frame)
                        if not ok: continue
                        await ws.send(buf.tobytes()); msg = await ws.recv()
                        try: data = json.loads(msg)
                        except json.JSONDecodeError: continue
                        
                        if which == "in" and data.get("plates"):
                            v_data = data["plates"][0]; plate = v_data.get("plate")
                            if self._should_show_popup(plate):
                                self._mark_popup_shown(plate)
                                asyncio.create_task(self.handle_checkin_request(v_data))
                        elif which == "out" and data.get("event") == "checkout_request":
                            t_data = data.get("ticket_data", {}); plate = t_data.get("plate")
                            if self._should_show_popup(plate): self._mark_popup_shown(plate); self.show_checkout_popup(t_data)
                        
                        if which == "in": self.frame_in = frame
                        else: self.frame_out = frame
            except Exception as e:
                print(f"[CLIENT] ⚠️ Camera {cam_id} bị ngắt: {e}"); await asyncio.sleep(RECONNECT_DELAY)

    # ✨ SỬA LỖI: Đây là hàm điều phối chính, quyết định popup nào sẽ được hiển thị
    async def handle_checkin_request(self, vehicle_data: dict):
        plate = vehicle_data.get("plate")
        if not plate:
            self._mark_popup_closed(plate) # Đảm bảo popup có thể hiện lại
            return
            
        print(f"[CLIENT] 🔎 Kiểm tra trạng thái của biển số {plate}...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_URL}/vehicle/status/{plate}") as resp:
                    if resp.status == 200:
                        status_data = await resp.json()
                        if status_data.get("is_monthly_active"):
                            # Nếu CÓ vé tháng -> Hiện popup xác nhận đơn giản
                            self.show_monthly_confirmation_popup(vehicle_data)
                        else:
                            # Nếu KHÔNG CÓ vé tháng -> Hiện popup chọn vé
                            self.show_ticket_choice_popup(vehicle_data)
                    else:
                        print(f"Lỗi kiểm tra trạng thái xe: {resp.status}. Hiển thị popup mặc định.")
                        self.show_ticket_choice_popup(vehicle_data)
        except Exception as e:
            print(f"Lỗi kết nối khi kiểm tra trạng thái xe: {e}. Hiển thị popup mặc định.")
            self.show_ticket_choice_popup(vehicle_data)

    def _should_show_popup(self, plate: str | None) -> bool:
        if not plate: return False
        current_time = time.time(); last_popup_time = self.popup_shown_for_plate.get(plate, 0)
        return (current_time - last_popup_time > self.popup_cooldown) and (plate not in self.active_popups)
    def _mark_popup_shown(self, plate: str): self.popup_shown_for_plate[plate] = time.time(); self.active_popups.add(plate)
    def _mark_popup_closed(self, plate: str):
        if plate in self.active_popups: self.active_popups.remove(plate)

    # ✨ CẢI TIẾN: Popup cho xe vé tháng, hiển thị đầy đủ thông tin
    def show_monthly_confirmation_popup(self, vehicle_data: dict):
        plate = vehicle_data.get("plate", "N/A")
        v_type = vehicle_data.get("vehicle_type", "N/A")
        
        msg = QMessageBox(self); msg.setWindowTitle("Xác Nhận Xe Vào")
        msg.setText(f"<b>Biển số:</b> {plate}<br>"
                    f"<b>Loại xe:</b> {v_type.capitalize()}<br>"
                    f"<b>Loại vé:</b> <span style='color: lime;'>Vé Tháng</span><br><br>"
                    f"Xác nhận cho xe vào bãi?")
        msg.setTextFormat(Qt.RichText); msg.setIcon(QMessageBox.Information)
        confirm_btn = msg.addButton("Xác Nhận Vào", QMessageBox.AcceptRole)
        msg.addButton("Hủy", QMessageBox.RejectRole)
        
        def on_close():
            self._mark_popup_closed(plate)
            if msg.clickedButton() == confirm_btn:
                asyncio.create_task(self.log_monthly_checkin(plate))
        msg.finished.connect(on_close); msg.open()

    # ✨ ĐỔI TÊN HÀM: Rõ ràng hơn, đây là popup để CHỌN vé
    def show_ticket_choice_popup(self, v_data: dict):
        car_id, plate, v_type, v_img_b64 = v_data.get("car_id"), v_data.get("plate"), v_data.get("vehicle_type"), v_data.get("vehicle_image_b64")
        
        msg = QMessageBox(self); msg.setWindowTitle("Lựa Chọn Loại Vé")
        msg.setText(f"<b>Xe:</b> {v_type or 'N/A'}<br><b>Biển số:</b> {plate}<br><br>Xe chưa đăng ký vé. Vui lòng chọn loại vé:")
        msg.setTextFormat(Qt.RichText)
        
        vis_btn = msg.addButton("Vé Lượt (3.000đ / 10.000đ)", QMessageBox.ActionRole)
        mon_btn = msg.addButton("Đăng Ký Vé Tháng", QMessageBox.ActionRole)
        msg.addButton("Hủy", QMessageBox.RejectRole)

        def on_close():
            clicked = msg.clickedButton()
            if clicked == vis_btn:
                self._mark_popup_closed(plate)
                asyncio.create_task(self.choose_ticket(car_id, plate, v_type, "hourly", v_img_b64))
            elif clicked == mon_btn:
                confirm_msg = QMessageBox(self); confirm_msg.setWindowTitle("Xác Nhận Đăng Ký Vé Tháng")
                confirm_msg.setText(f"Xác nhận đăng ký và thanh toán <b>60.000đ</b> cho vé tháng của xe <b>{plate}</b>?")
                confirm_msg.setTextFormat(Qt.RichText); confirm_msg.setIcon(QMessageBox.Question)
                yes_btn = confirm_msg.addButton("Đồng Ý", QMessageBox.AcceptRole)
                confirm_msg.addButton("Hủy", QMessageBox.RejectRole)
                
                confirm_msg.exec()
                self._mark_popup_closed(plate)
                if confirm_msg.clickedButton() == yes_btn:
                    asyncio.create_task(self.choose_ticket(car_id, plate, v_type, "monthly", v_img_b64))
            else:
                 self._mark_popup_closed(plate)
        msg.finished.connect(on_close); msg.open()

    def show_checkout_popup(self, ticket_data: dict):
        plate = ticket_data.get("plate", "N/A"); v_info = ticket_data.get("vehicle", {}); v_type = v_info.get("vehicle_type", "N/A")
        c_time_iso = ticket_data.get("checkin_time", ""); c_time_str = "N/A"
        if c_time_iso:
            try: c_time_str = datetime.fromisoformat(c_time_iso).strftime('%H:%M %d/%m/%Y')
            except (ValueError, TypeError): pass
        
        cost = ticket_data.get("cost", 0); formatted_cost = f"<b style='color: yellow; font-size: 18px;'>{cost:,} đ</b>"

        msg = QMessageBox(self); msg.setWindowTitle("Xác Nhận Xe Ra")
        msg.setText(f"<b>Xe:</b> {v_type}<br><b>Biển số:</b> {plate}<br><b>Giờ vào:</b> {c_time_str}<br><b>Giá tiền:</b> {formatted_cost}<br><br>Xác nhận cho xe này ra?")
        msg.setTextFormat(Qt.RichText); msg.setIcon(QMessageBox.Question)
        
        conf_btn = msg.addButton("Xác Nhận Ra", QMessageBox.AcceptRole); msg.addButton("Hủy", QMessageBox.RejectRole)
        def on_close():
            self._mark_popup_closed(plate)
            if msg.clickedButton() == conf_btn: asyncio.create_task(self.confirm_checkout(plate))
        msg.finished.connect(on_close); msg.open()

    def update_frames(self):
        if self.frame_in is not None: self._set_pixmap(self.video_label_in, self.frame_in)
        if self.frame_out is not None: self._set_pixmap(self.video_label_out, self.frame_out)
    def _set_pixmap(self, label, frame):
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB); h, w, ch = rgb_image.shape; bpl = ch * w
        qt_img = QImage(rgb_image.data, w, h, bpl, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img); pixmap = pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation); label.setPixmap(pixmap)

if __name__ == "__main__":
    import qasync
    app = QApplication(sys.argv)
    window = App()
    window.show()
    loop = qasync.QEventLoop(app); asyncio.set_event_loop(loop)
    with loop: loop.run_until_complete(window.start())
