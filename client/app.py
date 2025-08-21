import sys, asyncio, json, cv2
import websockets
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap
from frontend.home import ParkingDashboard

SERVER_URL = "ws://localhost:8000/ws/camera"
FRONTEND_ONLY = False  # 👈 bật cái này để không cần backend
RECONNECT_DELAY = 5    # số giây chờ khi mất kết nối

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


                            # vẽ bbox tại client
                            processed = self._draw_metadata(frame.copy(), data)

                            if which == "in":
                                self.frame_in = processed
                            else:
                                self.frame_out = processed

                except Exception as e:
                    print(f"[CLIENT] ⚠️ Camera {cam_id} disconnected: {e}")
                    await asyncio.sleep(RECONNECT_DELAY)


    def _draw_metadata(self, frame, data):
        if not isinstance(data, dict):
            return frame

        plates = data.get("plates", [])

        for item in plates:
            x1, y1, x2, y2 = map(int, item["bbox"])  # <-- giữ nguyên, KHÔNG nhân thêm scale
            plate = item.get("plate", "")
            conf = item.get("confidence", 0.0)

            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{plate} {conf:.2f}", (x1, max(0, y1 - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        return frame






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
