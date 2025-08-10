import cv2
from ultralytics import YOLO
from utils.readLicensePlate import readLicensePlate
from utils.utils import visualize

# load models
license_plate_detector = YOLO('models/yolo/best.pt')

# detect license plate
def yoloDetectPhoto(path):
    # load image
    img = cv2.imread(path)

    # detect license plate
    license_plates = license_plate_detector(img)[0]

    # extract license plate detection result
    for license_plate in license_plates.boxes.data.tolist():
        x1, y1, x2, y2, license_plateScore, license_plateClass_id = license_plate


        imgcpy = img.copy()
        license_plate = readLicensePlate(imgcpy, x1, y1, x2, y2)

        visualize(img,license_plateScore,license_plate[0],x1,y1,x2,y2)

        cv2.imwrite('resources/image/output/yolo/detection.jpg', img)
        return [license_plate[0], "resources/image/output/yolo/detection.jpg"]

