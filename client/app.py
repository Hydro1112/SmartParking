import sys, asyncio, json, cv2, base64
import websockets, aiohttp
import numpy as np
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from frontend.home import ParkingDashboard

SERVER_URL = "ws://localhost:8000/ws/camera"
API_URL = "http://localhost:8000/api"
FRONTEND_ONLY = False
RECONNECT_DELAY = 5

class App(ParkingDashboard):
    def __init__(self):
        super().__init__()
        # Lấy các widget video từ soatve_page
        self.video_label_in = self.soatve_page.mid_cam_in.video
        self.video_label_out = self.soatve_page.mid_cam_out.video
        self.frame_in, self.frame_out = None, None
        self.popup_shown_for_car = set()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frames)
        self.timer.start(30)

    async def start(self):
        await self.fetch_and_update_ui()
        await asyncio.gather(
            
            self.run_camera(0, "in"),
            self.run_camera(1, "out")
        )

    async def run_camera(self, cam_id: int, which: str):
        cap = cv2.VideoCapture(cam_id)
        if not cap.isOpened():
            print(f"[CLIENT] ❌ Cannot open webcam {cam_id}")
            return
        print(f"[CLIENT] ✅ Opened webcam {cam_id}")

        if FRONTEND_ONLY: # Chế độ chỉ chạy giao diện để test
            # ... (giữ nguyên)
            pass
        else:
            url = f"{SERVER_URL}/{cam_id}"
            while True:
                try:
                    async with websockets.connect(url) as ws:
                        print(f"[CLIENT] 🔗 Connected to server for cam {cam_id}")
                        while True:
                            ret, frame = cap.read()
                            if not ret: continue

                            ok, buf = cv2.imencode(".jpg", frame)
                            if not ok: continue
                            await ws.send(buf.tobytes())

                            msg = await ws.recv()
                            try:
                                data = json.loads(msg)
                            except json.JSONDecodeError:
                                print(f"[CLIENT] ⚠️ Non-JSON message: {msg}")
                                continue

                            # ✨ LOGIC MỚI: Cập nhật UI khi có sự kiện ✨
                            if data.get("plates"):
                                if which == "in":
                                    # Lấy thông tin xe đầu tiên từ danh sách
                                    vehicle_data = data["plates"][0]
                                    car_id = vehicle_data.get("car_id")

                                    # === THAY ĐỔI LOGIC TẠI ĐÂY ===
                                    # Chỉ hiển thị popup nếu chưa từng hiển thị cho xe này
                                    if car_id not in self.popup_shown_for_car:
                                        self.popup_shown_for_car.add(car_id) # Đánh dấu đã hiển thị
                                        print(f"[CLIENT] ✨ Showing popup for new car_id: {car_id}")

                                        first_plate = vehicle_data.get("plate")
                                        vehicle_type = vehicle_data.get("vehicle_type")
                                        self.show_ticket_popup(car_id, first_plate, vehicle_type)
                                    # ==============================
                                    
                                else: # Nếu là cổng ra, cập nhật ngay
                                    asyncio.create_task(self.fetch_and_update_ui())
                            # Cập nhật frame video
                            if which == "in": self.frame_in = frame
                            else: self.frame_out = frame

                except Exception as e:
                    print(f"[CLIENT] ⚠️ Camera {cam_id} disconnected: {e}")
                    await asyncio.sleep(RECONNECT_DELAY)

    def show_ticket_popup(self, car_id: int, plate: str, vehicle_type: str):
        msg = QMessageBox(self)
        msg.setWindowTitle("Chọn loại vé")
        msg.setText(f"Xe {vehicle_type} - Biển số {plate}\nChọn loại vé:")
        visitor_btn = msg.addButton("Vãng lai", QMessageBox.ActionRole)
        monthly_btn = msg.addButton("Vé tháng", QMessageBox.ActionRole)
        msg.addButton("Hủy", QMessageBox.RejectRole)

        # callback khi popup đóng
        def on_close():
            if msg.clickedButton() == visitor_btn: ticket_type = "hourly"
            elif msg.clickedButton() == monthly_btn: ticket_type = "monthly"
            else: return

            asyncio.create_task(self.choose_ticket(car_id, plate, vehicle_type, ticket_type))

        msg.finished.connect(on_close)
        msg.open()

    async def choose_ticket(self, car_id: int, plate: str, vehicle_type: str, ticket_type: str):
        """Gửi loại vé đã chọn lên server và sau đó cập nhật UI."""
        async with aiohttp.ClientSession() as session:
            payload = {
                "car_id": str(car_id), "plate": str(plate),
                "vehicle_type": str(vehicle_type), "ticket_type": str(ticket_type)
            }
            try:
                async with session.post(f"{API_URL}/ticket/choose", json=payload) as resp:
                    if resp.status == 200:
                        print(f"[CLIENT] ✅ Sent ticket choice: {payload}")
                        # Sau khi gửi thành công, gọi API để lấy dữ liệu mới nhất
                        await self.fetch_and_update_ui()
                    else:
                        print(f"[CLIENT] ❌ Failed to send ticket: {resp.status}")
            except Exception as e:
                print(f"[CLIENT] ⚠️ Error sending ticket: {e}")

   # app.py

# ... (các phần code khác giữ nguyên)

    async def fetch_and_update_ui(self):
        """Gọi API /history/latest và cập nhật giao diện."""
        print("[CLIENT] Fetching latest history to update UI...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_URL}/history/latest") as resp:
                    if resp.status == 200:
                        history_data = await resp.json()

                        # 👇 THAY THẾ TOÀN BỘ HÀM unwrap BẰNG ĐOẠN NÀY 👇
                        def unwrap(data):
                            if not data or not data.get("vehicle") or not data.get("history"):
                                return None
                            
                            vehicle = data.get("vehicle", {})
                            history = data.get("history", {})
                            ticket = data.get("ticket", {}) # Lấy thông tin vé

                            return {
                                "plate": vehicle.get("plate"),
                                "vehicle_type": vehicle.get("vehicle_type"),
                                # Lấy ảnh từ vehicle
                                "license_plate_image": vehicle.get("license_plate_image"),
                                # Lấy loại vé từ ticket
                                "ticket_type": ticket.get("ticket_type", "N/A"),
                                "time": ticket.get("time"),
                                "event_type": history.get("event_type")
                            }
                        # 👆 KẾT THÚC PHẦN THAY THẾ 👆

                        latest_in = unwrap(history_data.get("latest_in"))
                        latest_out = unwrap(history_data.get("latest_out"))

                        # Cập nhật card xe vào / xe ra
                        self.soatve_page.update_vehicle_info("in", latest_in)
                        self.soatve_page.update_vehicle_info("out", latest_out)

                    else:
                        print(f"[CLIENT] ❌ Failed to fetch history: {resp.status}")
        except Exception as e:
            print(f"[CLIENT] ⚠️ Error fetching history: {e}")

# ... (các phần code còn lại giữ nguyên)

    def update_frames(self):
        if self.frame_in is not None: self._set_pixmap(self.video_label_in, self.frame_in)
        if self.frame_out is not None: self._set_pixmap(self.video_label_out, self.frame_out)

    def _set_pixmap(self, label, frame):
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        pixmap = pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        label.setPixmap(pixmap)


if __name__ == "__main__":
    import qasync

    app = QApplication(sys.argv)
    window = App()
    window.show()

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    with loop:
        loop.run_until_complete(window.start())
