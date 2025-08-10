from models.faster_rcnn.detectron2.config import get_cfg
from models.faster_rcnn.detectron2.engine import DefaultPredictor
from models.faster_rcnn.detectron2 import model_zoo
from utils.readLicensePlate import readLicensePlate
from utils.utils import visualize
import cv2


def fasterRcnnDetectPhoto(path):

    # Load config from a config file
    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file('COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml'))
    cfg.MODEL.WEIGHTS = 'models/faster_rcnn/faster_rcnn.pth'
    cfg.MODEL.DEVICE = 'cpu'
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 2
    cfg.MODEL.ROI_HEADS.BATCH_SIZE_PER_IMAGE = 128

    # Create predictor instance
    predictor = DefaultPredictor(cfg)

    # Load image
    image = cv2.imread(path)

    # Perform prediction
    outputs = predictor(image)

    threshold = 0.8

    # Display predictions
    scores = outputs["instances"].scores.tolist()
    bboxes = outputs["instances"].pred_boxes

    for j, bbox in enumerate(bboxes):
        bbox = bbox.tolist()

        score = scores[j]

        if score > threshold:
            x1, y1, x2, y2 = [int(i) for i in bbox]

            imgcpy = image.copy()
            license_plate = readLicensePlate(imgcpy, x1, y1, x2, y2)

            visualize(image, score, license_plate[0], x1, y1, x2, y2)

            cv2.imwrite('resources/image/output/fasterRcnn/detection.jpg', image)
            return [license_plate[0], "resources/image/output/fasterRcnn/detection.jpg"]




