import cv2
import torch
import numpy as np
import time
from collections import deque, Counter
from torchvision.transforms import functional as F
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from ultralytics import YOLO

from server.utils.readLicensePlate import readLicensePlate
from server.sort.sort import Sort
from server.database import get_registered_plates, insert_plate_event, update_plate_event

# ---------------------- Config ----------------------
CAM_W, CAM_H = 480,480
YOLO_CONF = 0.20
PLATE_SCORE_THR = 0.9
FRAME_SKIP_INTERVAL = 5
VEHICLE_CLASSES = [2, 3]  # 2: car, 3: motorbike

# Majority vote
HISTORY_LEN = 5       # kích thước cửa sổ bỏ phiếu
MIN_VOTES = 3         # số phiếu tối thiểu để chấp nhận một biển số
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
    Pipeline: YOLO -> SORT -> Faster R-CNN -> OCR -> Majority Vote -> DB.
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

        # Lịch sử bỏ phiếu theo từng xe: car_id -> deque([...])
        self.car_plate_history = {}  # {car_id: deque([text1, text2, ...], maxlen=HISTORY_LEN)}

        # Biển số đã ghi vào DB theo từng xe: car_id -> (text, conf_gần_nhất)
        self.logged_cars = {}

        # Lưu "best" OCR theo conf nếu cần hiển thị tạm
        self.car_plate_best = {}  # car_id -> (best_text, best_conf)

    def process(self, frame: np.ndarray):
        """
        Nhận 1 BGR frame gốc (orig), trả về (frame_orig, metadata).
        metadata:
        {
            "plates": [
                {"car_id": int, "plate": str, "confidence": float, "votes": int, "bbox": [x1,y1,x2,y2]}
            ],
            "scale": {"orig_w": int, "orig_h": int, "input_w": int, "input_h": int}
        }

        - Detect/tracking/plate-detector chạy trên ảnh resize (input_w,input_h).
        - BBOX trong metadata đã được map về toạ độ ảnh gốc (orig_w, orig_h).
        - OCR cắt ảnh từ frame gốc để chất lượng tốt hơn.
        """
        if frame is None or frame.size == 0:
            return frame, {"plates": [], "scale": None}

        self.frame_count += 1
        metadata = {"plates": []}

        # Kích thước gốc
        orig_h, orig_w = frame.shape[:2]

        # Ảnh đưa vào model
        input_w, input_h = CAM_W, CAM_H
        infer_img = cv2.resize(frame, (input_w, input_h))  # ảnh cho YOLO/SORT/FRCNN

        # Hệ số scale từ infer -> original
        sx = float(orig_w) / float(input_w)
        sy = float(orig_h) / float(input_h)

        # Skip frame để tăng FPS (nếu cần)
        if FRAME_SKIP_INTERVAL > 1 and (self.frame_count % FRAME_SKIP_INTERVAL != 0):
            return frame, {
                "plates": [],
                "scale": {
                    "orig_w": orig_w, "orig_h": orig_h,
                    "input_w": input_w, "input_h": input_h
                }
            }

        # ---------------- YOLO detect vehicles (trên infer_img) ----------------
        try:
            yolo_pred = self.model_yolo(infer_img, verbose=False, half=self.YOLO_HALF)[0]
        except Exception:
            yolo_pred = self.model_yolo(infer_img, verbose=False)[0]

        dets = []
        # boxes.data: [x1,y1,x2,y2,score,cls] (tọa độ theo infer_img)
        for x1, y1, x2, y2, score, cls in yolo_pred.boxes.data.tolist():
            if int(cls) in VEHICLE_CLASSES and score >= YOLO_CONF:
                dets.append([x1, y1, x2, y2, score])
        dets_np = np.array(dets, dtype=float) if dets else np.empty((0, 5))

        # ---------------- SORT tracking (tọa độ theo infer_img) ----------------
        try:
            track_ids = self.tracker.update(dets_np)  # [x1,y1,x2,y2,id] theo infer_img
        except IndexError:
            track_ids = np.empty((0, 5))

        # ---------------- Faster-RCNN biển số trên từng vehicle (theo infer_img) ----------------
        crops = []
        car_map = []  # index -> (car_id, vx1, vy1, vx2, vy2) theo infer_img
        for vx1, vy1, vx2, vy2, car_id in track_ids.astype(int):
            vx1, vy1 = max(vx1, 0), max(vy1, 0)
            vx2, vy2 = min(vx2, input_w), min(vy2, input_h)
            if vx2 <= vx1 or vy2 <= vy1:
                continue

            vehicle_crop = infer_img[vy1:vy2, vx1:vx2]
            if vehicle_crop.size == 0:
                continue

            crops.append(_tensor_from_bgr(vehicle_crop))
            car_map.append((car_id, vx1, vy1, vx2, vy2))

        if crops:
            with torch.no_grad():
                outputs = self.model_frcnn(crops)

            for idx, out in enumerate(outputs):
                car_id, vx1, vy1, vx2, vy2 = car_map[idx]
                scores = out["scores"].cpu().numpy()
                labels = out["labels"].cpu().numpy()
                boxes = out["boxes"].cpu().numpy()

                for i, s in enumerate(scores):
                    if s < PLATE_SCORE_THR or labels[i] != 1:
                        continue

                    # Bbox plate trong toạ độ crop (infer_img)
                    px1, py1, px2, py2 = boxes[i].astype(int)
                    # Quy về toạ độ global (infer_img)
                    gx1, gy1 = vx1 + px1, vy1 + py1
                    gx2, gy2 = vx1 + px2, vy1 + py2

                    # Map từ infer_img -> ảnh gốc
                    ox1 = int(gx1 * sx)
                    oy1 = int(gy1 * sy)
                    ox2 = int(gx2 * sx)
                    oy2 = int(gy2 * sy)

                    # OCR cắt từ ảnh gốc (nét hơn)
                    plate_text, plate_conf = readLicensePlate(frame, ox1, oy1, ox2, oy2)

                    # Lưu best OCR theo conf
                    if plate_text:
                        if car_id not in self.car_plate_best or self.car_plate_best[car_id][1] < plate_conf:
                            self.car_plate_best[car_id] = (plate_text, plate_conf)

                    # Cập nhật history
                    if plate_text:
                        if car_id not in self.car_plate_history:
                            self.car_plate_history[car_id] = deque(maxlen=HISTORY_LEN)
                        self.car_plate_history[car_id].append(plate_text)

                    # Bỏ phiếu
                    best_text, best_count = "", 0
                    if car_id in self.car_plate_history and len(self.car_plate_history[car_id]) > 0:
                        votes = Counter(self.car_plate_history[car_id])
                        best_text, best_count = votes.most_common(1)[0]

                    draw_text = best_text if best_text else self.car_plate_best.get(car_id, ("", 0))[0]

                    # Metadata: bbox theo ẢNH GỐC
                    metadata["plates"].append({
                        "car_id": int(car_id),
                        "plate": draw_text,
                        "confidence": float(plate_conf),
                        "votes": int(best_count),
                        "bbox": [int(gx1), int(gy1), int(gx2), int(gy2)]
                    })

                    # DB update (có thể cân nhắc đẩy sang background để mượt hơn)
                    if best_text and best_count >= MIN_VOTES:
                        if car_id not in self.logged_cars:
                            insert_plate_event(car_id, best_text, self.event_label)
                            self.logged_cars[car_id] = (best_text, plate_conf)
                        else:
                            prev_text, prev_conf = self.logged_cars[car_id]
                            if best_text != prev_text:
                                update_plate_event(car_id, best_text)
                                self.logged_cars[car_id] = (best_text, plate_conf)
                            else:
                                if plate_conf > prev_conf:
                                    self.logged_cars[car_id] = (best_text, plate_conf)

        # Gửi kèm thông tin scale để client có thể tự xử lý nếu cần
        metadata["scale"] = {
            "orig_w": orig_w, "orig_h": orig_h,
            "input_w": input_w, "input_h": input_h
        }

        # Trả lại frame gốc (không vẽ) + metadata
        return metadata

