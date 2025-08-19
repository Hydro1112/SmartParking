import cv2
import torch
import numpy as np
from torchvision.transforms import functional as F
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from utils.readLicensePlate import readLicensePlate
from utils.utils import visualize
from sort.sort import Sort
from ultralytics import YOLO
import time

# ---- DB (SQLite) ----
from database import get_registered_plates, insert_plate_event, update_plate_event


# ---------------------- Config ----------------------
CAM_W, CAM_H = 320, 320
YOLO_CONF = 0.20
PLATE_SCORE_THR = 0.80
FRAME_SKIP_INTERVAL = 3
VEHICLE_CLASSES = [2, 3]  # 2: car, 3: motorcycle (tùy YOLO COCO)
LOG_INTERVAL = 10         # giây, tránh lưu trùng cho cùng một xe
# -----------------------------------------------------

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

def _tensor_from_bgr(img_bgr):
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    return F.to_tensor(img_rgb).to(device)

def _init_models():
    """Tạo model YOLO và Faster R-CNN riêng cho mỗi camera."""
    # Load Faster R-CNN (2 lớp: background + plate)
    model_frcnn = fasterrcnn_resnet50_fpn(weights=None)
    in_features = model_frcnn.roi_heads.box_predictor.cls_score.in_features
    model_frcnn.roi_heads.box_predictor = FastRCNNPredictor(in_features, 2)
    model_frcnn.load_state_dict(torch.load('models/faster_rcnn/faster_rcnn.pth', map_location=device))
    model_frcnn.to(device).eval()

    # Load YOLO
    model_yolo = YOLO('models/yolov8n.pt')
    YOLO_HALF = False
    if device.type == 'cuda':
        try:
            model_yolo.model.half()
            YOLO_HALF = True
        except Exception:
            YOLO_HALF = False

    return model_frcnn, model_yolo, YOLO_HALF
def _run_one_stream(cam_id, event_label, frame_queue):
    """
    cam_id: id camera (0/1/...)
    event_label: 'Entered' | 'Exited' (ghi vào DB)
    frame_queue: hàng đợi để push frame ra GUI
    """
    model_frcnn, model_yolo, YOLO_HALF = _init_models()
    mot_tracker = Sort()

    cap = cv2.VideoCapture(cam_id)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)

    registered_plates = get_registered_plates()

    prev_frame_time = 0.0
    frame_count = 0
    car_plate_best = {}
    last_plate_box = {}
    logged_cars = {}  # {car_id: (plate_text, confidence)}

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        # Skip frame để tăng FPS
        if FRAME_SKIP_INTERVAL > 1 and (frame_count % FRAME_SKIP_INTERVAL != 0):
            for car_id, (gx1, gy1, gx2, gy2, draw_text, last_seen) in list(last_plate_box.items()):
                if time.time() - last_seen < 1.0:
                    visualize(frame, 1.0, draw_text, gx1, gy1, gx2, gy2)
                else:
                    last_plate_box.pop(car_id, None)

            new_t = time.time()
            fps = 1.0 / (new_t - prev_frame_time + 1e-5)
            prev_frame_time = new_t
            cv2.putText(frame, f"FPS: {fps:.1f}", (7, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 2, (100, 255, 0), 3)
            frame_queue.put(frame)
            continue

        # YOLO detect vehicles
        try:
            yolo_kwargs = dict(verbose=False)
            if YOLO_HALF:
                yolo_kwargs['half'] = True
            yolo_pred = model_yolo(frame, **yolo_kwargs)[0]
        except Exception:
            yolo_pred = model_yolo(frame, verbose=False)[0]

        dets = []
        for det in yolo_pred.boxes.data.tolist():
            x1, y1, x2, y2, score, class_id = det
            if int(class_id) in VEHICLE_CLASSES and score >= YOLO_CONF:
                dets.append([x1, y1, x2, y2, score])

        dets_np = np.array(dets, dtype=float) if len(dets) > 0 else np.empty((0, 5), dtype=float)

        try:
            track_ids = mot_tracker.update(dets_np)
        except IndexError:
            track_ids = np.empty((0, 5))

        # Faster R-CNN trên crop vehicle
        for v in track_ids:
            vx1, vy1, vx2, vy2, car_id = v.astype(int)
            vx1 = max(vx1, 0); vy1 = max(vy1, 0)
            vx2 = min(vx2, frame.shape[1]); vy2 = min(vy2, frame.shape[0])
            if vx2 <= vx1 or vy2 <= vy1:
                continue

            vehicle_crop = frame[vy1:vy2, vx1:vx2]
            if vehicle_crop.size == 0:
                continue

            with torch.no_grad():
                outputs = model_frcnn([_tensor_from_bgr(vehicle_crop)])

            scores = outputs[0]['scores'].detach().cpu().numpy()
            labels = outputs[0]['labels'].detach().cpu().numpy()
            boxes = outputs[0]['boxes'].detach().cpu().numpy()

            found_plate = False

            for i, s in enumerate(scores):
                if s < PLATE_SCORE_THR or labels[i] != 1:
                    continue

                px1, py1, px2, py2 = boxes[i].astype(int)

                gx1 = vx1 + px1
                gy1 = vy1 + py1
                gx2 = vx2 - (vehicle_crop.shape[1] - px2)
                gy2 = vy2 - (vehicle_crop.shape[0] - py2)

                plate_text, plate_conf = readLicensePlate(frame.copy(), gx1, gy1, gx2, gy2)

                if car_id not in car_plate_best or car_plate_best[car_id][1] < plate_conf:
                    car_plate_best[car_id] = (plate_text, plate_conf)

                draw_text = plate_text if plate_text else car_plate_best.get(car_id, ("", 0.0))[0]
                visualize(frame, s, draw_text, gx1, gy1, gx2, gy2)

                last_plate_box[car_id] = (gx1, gy1, gx2, gy2, draw_text, time.time())
                found_plate = True

                # Chỉ log khi có text
                if draw_text:
                    if draw_text in registered_plates:
                        cv2.putText(frame, "Authorized...", (10, 400),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

                    if car_id not in logged_cars:
        # lần đầu log -> INSERT (có car_id)
                        insert_plate_event(car_id, draw_text, event_label)
                        logged_cars[car_id] = (draw_text, plate_conf)
                    else:
                        prev_text, prev_conf = logged_cars[car_id]
        # nếu đọc được bản tốt hơn thì UPDATE
                        if plate_conf > prev_conf and draw_text != prev_text:
                            update_plate_event(car_id, draw_text)
                            logged_cars[car_id] = (draw_text, plate_conf)


            if not found_plate and car_id in last_plate_box:
                gx1, gy1, gx2, gy2, draw_text, last_seen = last_plate_box[car_id]
                if time.time() - last_seen < 1.0:
                    visualize(frame, 1.0, draw_text, gx1, gy1, gx2, gy2)
                else:
                    last_plate_box.pop(car_id, None)

        # FPS overlay
        new_t = time.time()
        fps = 1.0 / (new_t - prev_frame_time + 1e-5)
        prev_frame_time = new_t
        cv2.putText(frame, f"FPS: {fps:.1f}", (7, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 2, (100, 255, 0), 3)

        frame_queue.put(frame)

    cap.release()


def fasterRcnnRealTimeDetectIn(frame_queue):
    _run_one_stream(0, "Entered", frame_queue)

def fasterRcnnRealTimeDetectOut(frame_queue):
    _run_one_stream(1, "Exited", frame_queue)
