import cv2
import torch
import numpy as np
from torchvision.transforms import functional as F
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from utils.readLicensePlate import readLicensePlate
from utils.utils import visualize, get_car
from datetime import datetime
from sort.sort import Sort
from ultralytics import YOLO
import time

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Load model torchvision Faster R-CNN và weights train của bạn
model = fasterrcnn_resnet50_fpn(weights=None)
num_classes = 2
in_features = model.roi_heads.box_predictor.cls_score.in_features
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
model.load_state_dict(torch.load('models/faster_rcnn/faster_rcnn.pth', map_location=device))
model.to(device)
model.eval()

mot_tracker = Sort()
coco_model = YOLO('models/yolov8n.pt')
vehicles = [2, 3, 5, 7]  # vehicle classes

def fasterRcnnRealTimeDetect():
    cap = cv2.VideoCapture(0)
    cap.set(3, 640)
    cap.set(4, 480)

    carPlate_dict = {}
    detected_license_plates = []

    prev_frame_time = 0

    # Đọc file registered_car_plate.txt 1 lần ngoài vòng lặp
    with open("resources/registered_car_plate.txt", 'r') as file:
        registered_plates = set(line.strip() for line in file.readlines())

    frame_skip_interval = 1  # mỗi 3 frame xử lý 1 lần
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % frame_skip_interval != 0:
            # Vẫn hiển thị FPS và frame nhưng không xử lý model
            new_frame_time = time.time()
            fps = 1/(new_frame_time - prev_frame_time + 1e-5)
            prev_frame_time = new_frame_time
            cv2.putText(frame, f"FPS: {fps:.1f}", (7, 70), cv2.FONT_HERSHEY_SIMPLEX, 2, (100,255,0), 3, cv2.LINE_AA)
            cv2.imshow('RealTime license Plate System', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        start_time = time.time()

        # Yolo detect vehicles
        detections = coco_model(frame)[0]
        detections_ = []
        for detection in detections.boxes.data.tolist():
            x1, y1, x2, y2, score, class_id = detection
            if int(class_id) in vehicles and score > 0.3:
                detections_.append([x1, y1, x2, y2, score])

        detections_np = np.array(detections_).reshape(-1, 5) if detections_ else np.empty((0,5))
        detections_bboxes = detections_np[:, :4] if len(detections_) > 0 else np.empty((0,4))
        track_ids = mot_tracker.update(np.asarray(detections_bboxes))

        # Run Faster-RCNN on full frame (or you can optimize to run on vehicle bbox crop)
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_tensor = F.to_tensor(img_rgb).to(device)

        with torch.no_grad():
            outputs = model([img_tensor])

        scores = outputs[0]['scores'].cpu().numpy()
        labels = outputs[0]['labels'].cpu().numpy()
        boxes = outputs[0]['boxes'].cpu().numpy()

        threshold = 0.8
        for i, score in enumerate(scores):
            if score < threshold:
                continue
            if labels[i] != 1:  # chỉ class plate
                continue

            x1, y1, x2, y2 = boxes[i].astype(int)

            license_plate = (x1, y1, x2, y2, score, "")
            xcar1, ycar1, xcar2, ycar2, car_id = get_car(license_plate, track_ids)
            frameCopy = frame.copy()

            licensePlate = "None"
            license_plate_result = readLicensePlate(frameCopy, x1, y1, x2, y2)

            if car_id in carPlate_dict:
                dict_license_plate, dict_license_plate_score = carPlate_dict[car_id][0]
                licensePlate = dict_license_plate

                if dict_license_plate_score < license_plate_result[1]:
                    carPlate_dict[car_id] = [(license_plate_result[0], license_plate_result[1])]
                    visualize(frame, score, license_plate_result[0], x1, y1, x2, y2)
                else:
                    visualize(frame, score, dict_license_plate, x1, y1, x2, y2)
            else:
                if car_id != -1:
                    if len(carPlate_dict) >= 10:
                        carPlate_dict.pop(next(iter(carPlate_dict)))
                    carPlate_dict[car_id] = [(license_plate_result[0], license_plate_result[1])]
                visualize(frame, score, license_plate_result[0], x1, y1, x2, y2)

            # So sánh với bộ biển đăng ký đã đọc 1 lần
            licensePlate = license_plate_result[0]
            if licensePlate in registered_plates:
                auth_text = "Authorized..."
                cv2.putText(frame, auth_text, (10, 400), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                with open("resources/entered_record.txt", "a") as file1:
                    if len(detected_license_plates) == 0 or detected_license_plates[-1] != licensePlate:
                        detected_license_plates.append(licensePlate)
                        file1.write(f"Plate Number: {licensePlate} : Entered at {datetime.now()}\n")

        # FPS
        new_frame_time = time.time()
        fps = 1/(new_frame_time - prev_frame_time + 1e-5)
        prev_frame_time = new_frame_time
        cv2.putText(frame, f"FPS: {fps:.1f}", (7, 70), cv2.FONT_HERSHEY_SIMPLEX, 2, (100,255,0), 3, cv2.LINE_AA)

        cv2.imshow('RealTime license Plate System', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    fasterRcnnRealTimeDetect()
