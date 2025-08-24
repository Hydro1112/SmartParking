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

from PySide6.QtWidgets import QApplication, QMessageBox, QInputDialog
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

    # ✨ HÀM HELPER 1: Tạo phiên bản async cho QInputDialog
    async def async_get_text_input(self, title: str, label: str) -> tuple[str, bool]:
        """Hiển thị QInputDialog một cách non-blocking."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        
        dialog = QInputDialog(self)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.setModal(True) # Đảm bảo nó luôn ở trên cùng

        def on_finish(result):
            # result là 1 nếu nhấn OK, 0 nếu Cancel
            text = dialog.textValue()
            if not future.done():
                future.set_result((text, bool(result)))

        dialog.finished.connect(on_finish)
        dialog.open() # Dùng .open() thay vì .exec() để không block

        return await future

    # ✨ HÀM HELPER 2: Tạo phiên bản async cho QMessageBox
    async def async_show_warning(self, title: str, text: str):
        """Hiển thị QMessageBox.warning một cách non-blocking."""
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setIcon(QMessageBox.Warning)

        def on_finish(_):
            if not future.done():
                future.set_result(None)

        msg_box.finished.connect(on_finish)
        msg_box.open()

        await future

    async def start(self):
        await self.update_status_cards(); await self.populate_initial_history()
        self.thongke_page.start_initial_fetch()
        self.tracuu_page.start_initial_fetch()
        await asyncio.gather(self.run_camera(0, "in"), self.run_camera(1, "out"))

    def _unwrap_history_data(self, data):
        if not data or not data.get("vehicle") or not data.get("history"): return None
        v, h, t = data.get("vehicle",{}), data.get("history",{}), data.get("ticket",{})
        
        # ✨ THAY ĐỔI 8: Sửa logic lấy thời gian. Ưu tiên timestamp của history.
        time_iso = h.get("timestamp") # Đây là nguồn chính xác nhất
        time_str = "---"
        
        if time_iso:
            try:
                time_str = datetime.fromisoformat(time_iso).strftime('%H:%M:%S %d/%m/%Y')
            except (ValueError, TypeError):
                print(f"Lỗi format thời gian: {time_iso}")
                pass
                
        return {
            "plate": v.get("plate"), 
            "vehicle_type": v.get("vehicle_type"), 
            "license_plate_image": v.get("license_plate_image"), 
            "ticket_type": t.get("ticket_type", "N/A"), 
            "time": time_str, 
            "event_type": h.get("event_type"), 
            "ticket_id": t.get("id")
        }
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

    async def _validate_checkout_on_server(self, plate: str, ticket_id: str) -> tuple[bool, str]:
        try:
            payload = {"plate": plate, "ticket_id": ticket_id}
            async with aiohttp.ClientSession() as session, session.post(f"{API_URL}/ticket/checkout", json=payload) as resp:
                if resp.status == 200:
                    return (True, "Xác nhận thành công!")
                else:
                    error_data = await resp.json()
                    error_detail = error_data.get("detail", "Lỗi không xác định từ server.")
                    return (False, error_detail)
        except Exception as e:
            error_msg = f"Lỗi kết nối đến server: {e}"
            print(f"[CLIENT] ⚠️ {error_msg}")
            return (False, error_msg)

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
                            if self._should_show_popup(plate):
                                self._mark_popup_shown(plate)
                                asyncio.create_task(self.show_checkout_popup(t_data))
                        
                        if which == "in": self.frame_in = frame
                        else: self.frame_out = frame
            except Exception as e:
                print(f"[CLIENT] ⚠️ Camera {cam_id} bị ngắt: {e}"); await asyncio.sleep(RECONNECT_DELAY)

    async def handle_checkin_request(self, vehicle_data: dict):
        plate = vehicle_data.get("plate")
        if not plate: self._mark_popup_closed(plate); return
        print(f"[CLIENT] 🔎 Kiểm tra trạng thái của biển số {plate}...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_URL}/vehicle/status/{plate}") as resp:
                    if resp.status == 200:
                        status_data = await resp.json()
                        if status_data.get("is_monthly_active"): self.show_monthly_confirmation_popup(vehicle_data)
                        else: self.show_ticket_choice_popup(vehicle_data)
                    else:
                        print(f"Lỗi kiểm tra trạng thái xe: {resp.status}. Hiển thị popup mặc định."); self.show_ticket_choice_popup(vehicle_data)
        except Exception as e:
            print(f"Lỗi kết nối khi kiểm tra trạng thái xe: {e}. Hiển thị popup mặc định."); self.show_ticket_choice_popup(vehicle_data)

    def _should_show_popup(self, plate: str | None) -> bool:
        if not plate: return False
        current_time = time.time(); last_popup_time = self.popup_shown_for_plate.get(plate, 0)
        return (current_time - last_popup_time > self.popup_cooldown) and (plate not in self.active_popups)
    def _mark_popup_shown(self, plate: str): self.popup_shown_for_plate[plate] = time.time(); self.active_popups.add(plate)
    def _mark_popup_closed(self, plate: str):
        if plate in self.active_popups: self.active_popups.remove(plate)

    def show_monthly_confirmation_popup(self, vehicle_data: dict):
        plate = vehicle_data.get("plate", "N/A"); v_type = vehicle_data.get("vehicle_type", "N/A")
        msg = QMessageBox(self); msg.setWindowTitle("Xác Nhận Xe Vào")
        msg.setText(f"<b>Biển số:</b> {plate}<br>"f"<b>Loại xe:</b> {v_type.capitalize()}<br>"f"<b>Loại vé:</b> <span style='color: lime;'>Vé Tháng</span><br><br>"f"Xác nhận cho xe vào bãi?")
        msg.setTextFormat(Qt.RichText); msg.setIcon(QMessageBox.Information)
        confirm_btn = msg.addButton("Xác Nhận Vào", QMessageBox.AcceptRole); msg.addButton("Hủy", QMessageBox.RejectRole)
        def on_close():
            self._mark_popup_closed(plate)
            if msg.clickedButton() == confirm_btn: asyncio.create_task(self.log_monthly_checkin(plate))
        msg.finished.connect(on_close); msg.open()

    def show_ticket_choice_popup(self, v_data: dict):
        car_id, plate, v_type, v_img_b64 = v_data.get("car_id"), v_data.get("plate"), v_data.get("vehicle_type"), v_data.get("vehicle_image_b64")
        msg = QMessageBox(self); msg.setWindowTitle("Lựa Chọn Loại Vé")
        msg.setText(f"<b>Xe:</b> {v_type or 'N/A'}<br><b>Biển số:</b> {plate}<br><br>Xe chưa đăng ký vé. Vui lòng chọn loại vé:")
        msg.setTextFormat(Qt.RichText)
        vis_btn = msg.addButton("Vé Lượt (3.000đ / 10.000đ)", QMessageBox.ActionRole); mon_btn = msg.addButton("Đăng Ký Vé Tháng", QMessageBox.ActionRole); msg.addButton("Hủy", QMessageBox.RejectRole)
        def on_close():
            clicked = msg.clickedButton()
            if clicked == vis_btn:
                self._mark_popup_closed(plate)
                asyncio.create_task(self.choose_ticket(car_id, plate, v_type, "hourly", v_img_b64))
            elif clicked == mon_btn:
                confirm_msg = QMessageBox(self); confirm_msg.setWindowTitle("Xác Nhận Đăng Ký Vé Tháng")
                confirm_msg.setText(f"Xác nhận đăng ký và thanh toán <b>60.000đ</b> cho vé tháng của xe <b>{plate}</b>?")
                confirm_msg.setTextFormat(Qt.RichText); confirm_msg.setIcon(QMessageBox.Question)
                yes_btn = confirm_msg.addButton("Đồng Ý", QMessageBox.AcceptRole); confirm_msg.addButton("Hủy", QMessageBox.RejectRole)
                confirm_msg.exec() # Dùng exec ở đây vẫn ổn vì nó nằm trong một slot đồng bộ
                self._mark_popup_closed(plate)
                if confirm_msg.clickedButton() == yes_btn: asyncio.create_task(self.choose_ticket(car_id, plate, v_type, "monthly", v_img_b64))
            else: self._mark_popup_closed(plate)
        msg.finished.connect(on_close); msg.open()

    # ✨ SỬA LẠI HÀM NÀY ĐỂ DÙNG HELPER ASYNC
    async def show_checkout_popup(self, ticket_data: dict):
        plate = ticket_data.get("plate", "N/A"); v_info = ticket_data.get("vehicle", {}); v_type = v_info.get("vehicle_type", "N/A")
        c_time_iso = ticket_data.get("checkin_time", ""); c_time_str = "N/A"
        if c_time_iso:
            try: c_time_str = datetime.fromisoformat(c_time_iso).strftime('%H:%M %d/%m/%Y')
            except (ValueError, TypeError): pass
        
        cost = ticket_data.get("cost", 0); formatted_cost = f"<b style='color: yellow; font-size: 18px;'>{cost:,} đ</b>"
        dialog_title = "Xác Nhận Xe Ra"
        dialog_label_text = (f"<b>Xe:</b> {v_type}<br>"
                             f"<b>Biển số:</b> {plate}<br>"
                             f"<b>Giờ vào:</b> {c_time_str}<br>"
                             f"<b>Giá tiền:</b> {formatted_cost}<br><br>"
                             f"<b>Vui lòng nhập MÃ VÉ để xác nhận:</b>")
        
        while True:
            entered_ticket_id, ok = await self.async_get_text_input(dialog_title, dialog_label_text)

            if not ok:
                print(f"[CLIENT] Người dùng đã hủy checkout cho xe {plate}")
                break 

            if not entered_ticket_id.strip():
                await self.async_show_warning("Lỗi", "Mã vé không được để trống. Vui lòng nhập lại.")
                continue 

            is_valid, message = await self._validate_checkout_on_server(plate, entered_ticket_id.strip().upper())

            if is_valid:
                print(f"[CLIENT] ✅ Đã xác nhận checkout: {plate}")
                await self.handle_new_event("out")
                break 
            else:
                await self.async_show_warning("Xác Nhận Thất Bại", message)
        
        # Dù thành công hay hủy, cuối cùng cũng giải phóng popup
        self._mark_popup_closed(plate)

    def update_frames(self):
        if self.frame_in is not None: self._set_pixmap(self.video_label_in, self.frame_in)
        if self.frame_out is not None: self._set_pixmap(self.video_label_out, self.frame_out)
    def _set_pixmap(self, label, frame):
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB); h, w, ch = rgb_image.shape; bpl = ch * w
        qt_img = QImage(rgb_image.data, w, h, bpl, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img); pixmap = pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation); label.setPixmap(pixmap)

if __name__ == "__main__":
    import qasync
    
    async def main():
        # Hàm main bất đồng bộ để khởi tạo và chạy ứng dụng
        
        def close_future(future, loop):
            loop.call_later(10, future.cancel)
            future.cancel()

        loop = asyncio.get_event_loop()
        future = asyncio.Future()

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Thiết lập qasync để tích hợp với vòng lặp sự kiện của app
        event_loop = qasync.QEventLoop(app)
        asyncio.set_event_loop(event_loop)

        app.aboutToQuit.connect(lambda: close_future(future, loop))

        # Khởi tạo cửa sổ chính
        main_window = App()
        main_window.showMaximized()
        main_window.show()

        # Bắt đầu các tác vụ bất đồng bộ của cửa sổ
        await main_window.start()

        # Chạy vòng lặp sự kiện cho đến khi ứng dụng đóng
        await future
        return True

    try:
        qasync.run(main())
    except asyncio.exceptions.CancelledError:
        sys.exit(0)