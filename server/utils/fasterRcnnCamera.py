import cv2
import torch
import numpy as np
import time
from torchvision.transforms import functional as F
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from ultralytics import YOLO

from server.utils.readLicensePlate import readLicensePlate
from server.utils.utils import visualize
from server.sort.sort import Sort
from server.database import get_registered_plates, insert_plate_event, update_plate_event

# ---------------------- Config ----------------------
CAM_W, CAM_H = 320, 320
YOLO_CONF = 0.20
PLATE_SCORE_THR = 0.99
FRAME_SKIP_INTERVAL = 3
VEHICLE_CLASSES = [2, 3]  # 2: car, 3: motorbike
# -----------------------------------------------------

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


def _tensor_from_bgr(img_bgr):
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    return F.to_tensor(img_rgb).to(device)


def _init_models():
    """Tải YOLO + Faster R-CNN một lần."""
    # Faster R-CNN (2 lớp: background + plate)
    model_frcnn = fasterrcnn_resnet50_fpn(weights=None)
    in_features = model_frcnn.roi_heads.box_predictor.cls_score.in_features
    model_frcnn.roi_heads.box_predictor = FastRCNNPredictor(in_features, 2)
    model_frcnn.load_state_dict(torch.load("server/models/faster_rcnn.pth", map_location=device))
    model_frcnn.to(device).eval()

    # YOLO
    model_yolo = YOLO("server/models/yolov8n.pt")
    YOLO_HALF = False
    if device.type == "cuda":
        try:
            model_yolo.model.half()
            YOLO_HALF = True
        except Exception:
            pass

    return model_frcnn, model_yolo, YOLO_HALF


class PlateDetector:
    """
    Dùng class này để xử lý từng frame nhận từ client qua WebSocket.
    Giữ nguyên pipeline: YOLO -> SORT -> Faster R-CNN -> VietOCR -> DB.
    """
    _shared_models = None  # cache models giữa nhiều instance

    def __init__(self, event_label: str = "in"):
        if PlateDetector._shared_models is None:
            PlateDetector._shared_models = _init_models()
        self.model_frcnn, self.model_yolo, self.YOLO_HALF = PlateDetector._shared_models

        self.tracker = Sort()
        self.event_label = event_label
        self.registered_plates = get_registered_plates()

        # state theo stream
        self.prev_frame_time = time.time()
        self.frame_count = 0
        self.car_plate_best = {}  # car_id -> (best_text, best_conf)
        self.logged_cars = {}     # car_id -> (last_text, last_conf)

    def process(self, frame: np.ndarray):
        """
        Nhận 1 BGR frame, trả về (frame_đã_vẽ, metadata).
        metadata: {"plates": [{"car_id": int, "plate": str, "confidence": float}, ...]}
        """
        if frame is None or frame.size == 0:
            return frame, {"plates": []}

        self.frame_count += 1
        metadata = {"plates": []}

        # (tuỳ bạn có muốn resize/truncate để đảm bảo kích thước…)
        # cv2.resize nếu cần
        frame = cv2.resize(frame, (CAM_W, CAM_H))

        # Skip frame để tăng FPS (giữ nhịp cho tracker/fps overlay)
        if FRAME_SKIP_INTERVAL > 1 and (self.frame_count % FRAME_SKIP_INTERVAL != 0):
            self._put_fps(frame)
            return frame, metadata

        # YOLO detect vehicles
        try:
            yolo_pred = self.model_yolo(frame, verbose=False, half=self.YOLO_HALF)[0]
        except Exception:
            yolo_pred = self.model_yolo(frame, verbose=False)[0]

        dets = []
        # boxes.data: [x1,y1,x2,y2,score,cls]
        for x1, y1, x2, y2, score, cls in yolo_pred.boxes.data.tolist():
            if int(cls) in VEHICLE_CLASSES and score >= YOLO_CONF:
                dets.append([x1, y1, x2, y2, score])
        dets_np = np.array(dets, dtype=float) if dets else np.empty((0, 5))

        # SORT tracking (trả về [x1,y1,x2,y2,id])
        try:
            track_ids = self.tracker.update(dets_np)
        except IndexError:
            track_ids = np.empty((0, 5))

        # detect plate với Faster R-CNN trên mỗi vehicle
        for vx1, vy1, vx2, vy2, car_id in track_ids.astype(int):
            vx1, vy1 = max(vx1, 0), max(vy1, 0)
            vx2, vy2 = min(vx2, frame.shape[1]), min(vy2, frame.shape[0])
            if vx2 <= vx1 or vy2 <= vy1:
                continue

            vehicle_crop = frame[vy1:vy2, vx1:vx2]
            if vehicle_crop.size == 0:
                continue

            with torch.no_grad():
                outputs = self.model_frcnn([_tensor_from_bgr(vehicle_crop)])
            scores = outputs[0]["scores"].cpu().numpy()
            labels = outputs[0]["labels"].cpu().numpy()
            boxes = outputs[0]["boxes"].cpu().numpy()

            for i, s in enumerate(scores):
                # label 1 là "plate" như logic cũ
                if s < PLATE_SCORE_THR or labels[i] != 1:
                    continue

                px1, py1, px2, py2 = boxes[i].astype(int)
                gx1, gy1 = vx1 + px1, vy1 + py1
                gx2, gy2 = vx1 + px2, vy1 + py2

                plate_text, plate_conf = readLicensePlate(frame.copy(), gx1, gy1, gx2, gy2)
                if car_id not in self.car_plate_best or self.car_plate_best[car_id][1] < plate_conf:
                    self.car_plate_best[car_id] = (plate_text, plate_conf)

                draw_text = plate_text or self.car_plate_best.get(car_id, ("", 0))[0]
                visualize(frame, s, draw_text, gx1, gy1, gx2, gy2)  # giữ giao diện vẽ cũ

                metadata["plates"].append({
                    "car_id": int(car_id),
                    "plate": draw_text,
                    "confidence": float(plate_conf)
                })

                # Ghi lịch sử vào DB (logic cũ)
                if draw_text:
                    if car_id not in self.logged_cars:
                        insert_plate_event(car_id, draw_text, self.event_label)
                        self.logged_cars[car_id] = (draw_text, plate_conf)
                    else:
                        prev_text, prev_conf = self.logged_cars[car_id]
                        if plate_conf > prev_conf and draw_text != prev_text:
                            update_plate_event(car_id, draw_text)
                            self.logged_cars[car_id] = (draw_text, plate_conf)

        # FPS overlay
        self._put_fps(frame)
        return frame, metadata

    def _put_fps(self, frame):
        new_t = time.time()
        fps = 1.0 / (new_t - self.prev_frame_time + 1e-5)
        self.prev_frame_time = new_t
        cv2.putText(frame, f"FPS: {fps:.1f}", (7, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 255, 0), 2)
