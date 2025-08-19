import sys
import queue
from threading import Thread
import cv2
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QPixmap

from frontend.home import ParkingDashboard
from models.faster_rcnn.fasterRcnnCamera import (
    fasterRcnnRealTimeDetectIn,
    fasterRcnnRealTimeDetectOut
)
from database import init_db
init_db()

# Queue để nhận frame từ thread camera
queue_in = queue.Queue(maxsize=1)
queue_out = queue.Queue(maxsize=1)

def camera_exists(cam_id: int) -> bool:
    """Kiểm tra camera có kết nối không."""
    cap = cv2.VideoCapture(cam_id)
    ok = cap.isOpened()
    cap.release()
    return ok

class App(ParkingDashboard):
    def __init__(self):
        super().__init__()

        # Xóa widget mặc định
        self.soatve_page.cam_left.v.takeAt(0).widget().deleteLater()
        self.soatve_page.cam_right.v.takeAt(0).widget().deleteLater()

# Thêm QLabel thay thế
        self.video_label_in = QLabel("Không kết nối được Camera Vào")
        self.video_label_in.setAlignment(Qt.AlignCenter)
        self.soatve_page.cam_left.v.addWidget(self.video_label_in)

        self.video_label_out = QLabel("Không kết nối được Camera Ra")
        self.video_label_out.setAlignment(Qt.AlignCenter)
        self.soatve_page.cam_right.v.addWidget(self.video_label_out)


        # Kiểm tra camera
        self.has_cam_in = camera_exists(0)
        self.has_cam_out = camera_exists(1)

        if self.has_cam_in:
            self.video_label_in.setText("Camera Vào - Đang kết nối...")
            Thread(target=fasterRcnnRealTimeDetectIn, args=(queue_in,), daemon=True).start()

        if self.has_cam_out:
            self.video_label_out.setText("Camera Ra - Đang kết nối...")
            Thread(target=fasterRcnnRealTimeDetectOut, args=(queue_out,), daemon=True).start()

        # Timer cập nhật frame
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frames)
        self.timer.start(30)

    def update_frames(self):
        """Cập nhật hình ảnh từ camera nếu có."""
        if self.has_cam_in:
            self._update_label_from_queue(self.video_label_in, queue_in)
        if self.has_cam_out:
            self._update_label_from_queue(self.video_label_out, queue_out)

    def _update_label_from_queue(self, label, frame_queue):
        try:
            frame = frame_queue.get_nowait()
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            label.setPixmap(QPixmap.fromImage(qt_image).scaled(
                label.width(), label.height(), Qt.KeepAspectRatio))
        except queue.Empty:
            pass


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())
