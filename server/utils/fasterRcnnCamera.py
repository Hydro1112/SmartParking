import cv2
import torch
import numpy as np
from collections import deque, Counter
from torchvision.transforms import functional as F
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from ultralytics import YOLO
import base64
from server.utils.readLicensePlate import readLicensePlate
from server.sort.sort import Sort

# Thay đổi import: Bỏ các hàm DB cũ, import lớp Model 'Vehicle'
from server.database.database_manager import DatabaseManager, Vehicle

# ---------------------- Config ----------------------
CAM_W, CAM_H = 480, 480
YOLO_CONF = 0.20
PLATE_SCORE_THR = 0.9
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
    Pipeline: (ảnh resize) YOLO -> SORT -> Faster R-CNN -> OCR -> Majority Vote.
    Ảnh gốc chỉ để gửi về client.
    """
    _shared_models = None  # cache models giữa nhiều instance

    # Thay đổi __init__: Thêm db_manager làm tham số
    def __init__(self, db_manager: DatabaseManager, event_label=None):
        if PlateDetector._shared_models is None:
            PlateDetector._shared_models = _init_models()
        self.model_frcnn, self.model_yolo, self.YOLO_HALF = PlateDetector._shared_models

        self.tracker = Sort()
        self.db_manager = db_manager  # Lưu lại instance của manager

        # Lịch sử bỏ phiếu theo từng xe: car_id -> deque([...])
        self.car_plate_history = {}  # {car_id: deque([...], maxlen=HISTORY_LEN)}

        # Biển số đã log theo từng xe: car_id -> (text, conf)
        self.logged_cars = {}

        # Thêm event_label (in/out)
        self.event_label = event_label

    def process(self, frame: np.ndarray):
        """
        Trả về metadata JSON:
        {
            "plates": [...],
            "image_full": <base64 ảnh gốc>,
            "event": "in"/"out"
        }
        """
        if frame is None or frame.size == 0:
            return {"plates": [], "image_full": None, "event": self.event_label}

        metadata = {"plates": []}

        # ---------------- Resize toàn bộ pipeline detect ----------------
        detect_img = cv2.resize(frame, (CAM_W, CAM_H))

        # ---------------- YOLO detect ----------------
        try:
            yolo_pred = self.model_yolo(detect_img, verbose=False, half=self.YOLO_HALF)[0]
        except Exception:
            yolo_pred = self.model_yolo(detect_img, verbose=False)[0]

        dets, car_info = [], []
        for x1, y1, x2, y2, score, cls in yolo_pred.boxes.data.tolist():
            if int(cls) in VEHICLE_CLASSES and score >= YOLO_CONF:
                dets.append([x1, y1, x2, y2, score])
                car_type = "car" if int(cls) == 2 else "motorbike"
                car_info.append((x1, y1, x2, y2, car_type))
        dets_np = np.array(dets, dtype=float) if dets else np.empty((0, 5))

        # ---------------- SORT tracking ----------------
        try:
            track_ids = self.tracker.update(dets_np)
        except IndexError:
            track_ids = np.empty((0, 5))

        # ---------------- Faster-RCNN + OCR ----------------
        for idx, (vx1, vy1, vx2, vy2, car_id) in enumerate(track_ids.astype(int)):
            vx1, vy1, vx2, vy2 = map(int, [vx1, vy1, vx2, vy2])
            vehicle_crop = detect_img[vy1:vy2, vx1:vx2]
            if vehicle_crop.size == 0:
                continue

            with torch.no_grad():
                outputs = self.model_frcnn([_tensor_from_bgr(vehicle_crop)])

            out = outputs[0]
            for i, s in enumerate(out["scores"].cpu().numpy()):
                if s < PLATE_SCORE_THR or out["labels"][i].item() != 1:
                    continue

                px1, py1, px2, py2 = out["boxes"][i].cpu().numpy().astype(int)
                ox1, oy1 = vx1 + px1, vy1 + py1
                ox2, oy2 = vx1 + px2, vy1 + py2

                # OCR chạy trên ảnh resize
                plate_text, plate_conf = readLicensePlate(detect_img, ox1, oy1, ox2, oy2)
                if not plate_text:
                    continue

                # Bỏ phiếu
                if car_id not in self.car_plate_history:
                    self.car_plate_history[car_id] = deque(maxlen=HISTORY_LEN)
                self.car_plate_history[car_id].append(plate_text)
                votes = Counter(self.car_plate_history[car_id])
                best_text, best_count = votes.most_common(1)[0]

                # Chỉ add nếu đã vote đủ
                if best_count >= MIN_VOTES:
                    plate_text = best_text
                    vehicle_type = car_info[idx][4] if idx < len(car_info) else "unknown"

                    # Thay thế logic DB cũ bằng DatabaseManager
                    # =========================================================
                    # 1. Kiểm tra xe đã có trong DB chưa bằng biển số
                    existing_vehicle = self.db_manager.get_vehicle_by_plate(plate_text)

                    # 2. Nếu xe chưa có, tạo bản ghi mới
                    if existing_vehicle is None:
                        # Convert ảnh crop sang base64
                        _, buf = cv2.imencode(".jpg", vehicle_crop)
                        img_b64 = base64.b64encode(buf).decode("utf-8")
                        
                        # Tạo đối tượng Vehicle
                        new_vehicle = Vehicle(
                            id=str(car_id),
                            plate=plate_text,
                            vehicle_type=vehicle_type,
                            license_plate_image=img_b64
                        )
                        # Dùng manager để tạo
                        self.db_manager.create_vehicle(new_vehicle)
                        print(f"[AI] 🆕 Xe mới được phát hiện và lưu vào DB: {plate_text}")
                    # =========================================================

                    metadata["plates"].append({
                        "car_id": int(car_id),
                        "plate": plate_text,
                        "vehicle_type": vehicle_type
                    })


        # ---------------- Gửi kèm ảnh gốc ----------------
        _, buf = cv2.imencode(".jpg", frame)
        metadata["image_full"] = base64.b64encode(buf).decode("utf-8")

        # ---------------- Thêm event (in/out) ----------------
        metadata["event"] = self.event_label
        
        return metadata

