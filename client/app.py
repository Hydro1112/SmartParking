import sys, asyncio, json, cv2
import websockets
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from frontend.home import ParkingDashboard

SERVER_URL = "ws://localhost:8000/ws/camera"
FRONTEND_ONLY = False  # 👈 bật cái này để không cần backend


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
            # 👉 Không connect WS, chỉ đọc webcam
            while True:
                ret, frame = cap.read()
                if not ret:
                    print(f"[CLIENT] ❌ Failed to capture frame from webcam {cam_id}")
                    await asyncio.sleep(0.03)
                    continue

                if which == "in":
                    self.frame_in = frame
                else:
                    self.frame_out = frame

                await asyncio.sleep(0.03)  # tránh full CPU
        else:
            # 👉 Chế độ có backend, vừa gửi vừa nhận frame
            url = f"{SERVER_URL}/{cam_id}"
            async with websockets.connect(url) as ws:
                print(f"[CLIENT] 🔗 Connected to server for cam {cam_id}")
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        continue

                    ok, buf = cv2.imencode(".jpg", frame)
                    if not ok:
                        continue

                    await ws.send(buf.tobytes().hex())
                    msg = await ws.recv()
                    data = json.loads(msg)

                    frame_bytes = bytes.fromhex(data["frame"])
                    arr = np.frombuffer(frame_bytes, dtype=np.uint8)
                    processed = cv2.imdecode(arr, cv2.IMREAD_COLOR)

                    if which == "in":
                        self.frame_in = processed
                    else:
                        self.frame_out = processed

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
