import sys, asyncio, json, cv2, base64
import websockets, aiohttp
import numpy as np
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from frontend.home import ParkingDashboard

SERVER_URL = "ws://localhost:8000/ws/camera"
API_URL = "http://localhost:8000/api/ticket/choose"  # REST API để chọn vé
FRONTEND_ONLY = False
RECONNECT_DELAY = 5

class App(ParkingDashboard):
    def __init__(self):
        super().__init__()
        self.video_label_in = self.soatve_page.mid_cam_in.video
        self.video_label_out = self.soatve_page.mid_cam_out.video
        self.frame_in, self.frame_out = None, None

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frames)
        self.timer.start(30)

    async def start(self):
        # Chạy 2 camera song song
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

        if FRONTEND_ONLY:
            while True:
                ret, frame = cap.read()
                if not ret:
                    await asyncio.sleep(0.03)
                    continue

                if which == "in":
                    self.frame_in = frame
                else:
                    self.frame_out = frame

                await asyncio.sleep(0.03)
        else:
            url = f"{SERVER_URL}/{cam_id}"
            while True:
                try:
                    async with websockets.connect(url) as ws:
                        print(f"[CLIENT] 🔗 Connected to server for cam {cam_id}")
                        while True:
                            ret, frame = cap.read()
                            if not ret:
                                continue

                            # gửi raw JPG byte
                            ok, buf = cv2.imencode(".jpg", frame)
                            if not ok:
                                continue
                            await ws.send(buf.tobytes())

                            # nhận JSON metadata
                            msg = await ws.recv()
                            try:
                                data = json.loads(msg)
                            except json.JSONDecodeError:
                                print(f"[CLIENT] ⚠️ Non-JSON message: {msg}")
                                continue

                            # Nếu là cổng vào thì hiển thị popup chọn vé
                            if which == "in" and data.get("plates"):
                                first_plate = self.get_first_plate(data)
                                vehicle_type = self.get_vehicle_types(data)[0]
                                car_id = data["plates"][0].get("car_id")

                                # popup chọn vé
                                self.show_ticket_popup(car_id, first_plate, vehicle_type)

                            # Cập nhật frame (ảnh gốc không vẽ bbox)
                            if which == "in":
                                self.frame_in = frame
                            else:
                                self.frame_out = frame

                except Exception as e:
                    print(f"[CLIENT] ⚠️ Camera {cam_id} disconnected: {e}")
                    await asyncio.sleep(RECONNECT_DELAY)

    # ===================== JSON Getters =====================
    def get_all_plates(self, data: dict):
        return [item.get("plate") for item in data.get("plates", [])]

    def get_first_plate(self, data: dict):
        plates = self.get_all_plates(data)
        return plates[0] if plates else None

    def get_vehicle_types(self, data: dict):
        return [item.get("vehicle_type") for item in data.get("plates", [])]

    def get_image_full(self, data: dict):
        return data.get("image_full")

    # ===================== Ticket Popup + API =====================
    def show_ticket_popup(self, car_id: int, plate: str, vehicle_type: str):
        msg = QMessageBox()
        msg.setWindowTitle("Chọn loại vé")
        msg.setText(f"Xe {vehicle_type} - Biển số {plate}\nChọn loại vé:")
        visitor_btn = msg.addButton("Visitor", QMessageBox.ActionRole)
        monthly_btn = msg.addButton("Monthly", QMessageBox.ActionRole)
        cancel_btn = msg.addButton("Hủy", QMessageBox.RejectRole)

        msg.exec()

        if msg.clickedButton() == visitor_btn:
            ticket_type = "visitor"
        elif msg.clickedButton() == monthly_btn:
            ticket_type = "monthly"
        else:
            return  # không chọn gì

        asyncio.create_task(self.choose_ticket(car_id, plate, vehicle_type, ticket_type))

    async def choose_ticket(self, car_id: int, plate: str, vehicle_type: str, ticket_type: str):
        """Gửi loại vé đã chọn lên server"""
        async with aiohttp.ClientSession() as session:
            payload = {
                "car_id": car_id,
                "plate": plate,
                "vehicle_type": vehicle_type,
                "ticket_type": ticket_type
            }
            try:
                async with session.post(API_URL, json=payload) as resp:
                    if resp.status == 200:
                        print(f"[CLIENT] ✅ Sent ticket choice: {payload}")
                    else:
                        print(f"[CLIENT] ❌ Failed to send ticket: {resp.status}")
            except Exception as e:
                print(f"[CLIENT] ⚠️ Error sending ticket: {e}")

    # ===================== UI Update =====================
    def update_frames(self):
        if self.frame_in is not None:
            self._set_pixmap(self.video_label_in, self.frame_in)
        if self.frame_out is not None:
            self._set_pixmap(self.video_label_out, self.frame_out)

    def _set_pixmap(self, label, frame):
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)

        pixmap = QPixmap.fromImage(qt_image)
        pixmap = pixmap.scaled(
            label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
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
