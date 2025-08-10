import cv2
from ultralytics import YOLO
from utils.utils import get_car
from utils.readLicensePlate import readLicensePlate
from utils.utils import visualize
from sort.sort import *
from datetime import datetime

# load models
mot_tracker = Sort()
coco_model = YOLO('models/yolov8n.pt')
license_plate_detector = YOLO('models/yolo/best.pt')
def yoloRealTimeModelDetect():

    # Configure Camera
    cap = cv2.VideoCapture(1)
    cap.set(3, 640)
    cap.set(4, 480)
    vehicles = [2, 3, 5, 7]
    threshold = 0.8
    # Declare CarPlate dictionary
    carPlate_dict = {}
    detected_license_plates = []

    # used to record the time when we processed last frame
    prev_frame_time = 0

    # used to record the time at which we processed current frame
    new_frame_time = 0

    while True:
        ret, frame = cap.read()
        # Yolo COCO pretrained model detection
        detections = coco_model(frame)[0]
        detections_ = []

        # time when we finish processing for this frame
        new_frame_time = time.time()

        # Calculating the fps

        # fps will be number of frame processed in given time frame
        # since their will be most of time error of 0.001 second
        # we will be subtracting it to get more accurate result
        fps = 1 / (new_frame_time - prev_frame_time)
        prev_frame_time = new_frame_time

        # converting the fps into integer
        fps = int(fps)

        # converting the fps to string so that we can display it on frame
        # by using putText function
        fps = str(fps)

        # putting the FPS count on the frame
        cv2.putText(frame, fps, (7, 70), cv2.FONT_HERSHEY_SIMPLEX, 3, (100, 255, 0), 3, cv2.LINE_AA)

        # Yolo COCO pretrained model result
        for detection in detections.boxes.data.tolist():
            x1, y1, x2, y2, score, class_id = detection
            if int(class_id) in vehicles:
                detections_.append([x1, y1, x2, y2, score])

        # track vehicles
        detections_np = np.array(detections_).reshape(-1, 5)
        detections_bboxes = detections_np[:, :4]
        track_ids = mot_tracker.update(np.asarray(detections_bboxes))

        # detect license plates
        license_plates = license_plate_detector(frame)[0]
        for license_plate in license_plates.boxes.data.tolist():
            x1, y1, x2, y2, score, class_id = license_plate


            # assign license plate to car
            xcar1, ycar1, xcar2, ycar2, car_id = get_car(license_plate, track_ids)
            frameCopy = frame.copy()

            licensePlate = "None"

            # run license plate recognition
            license_plate_result = readLicensePlate(frameCopy, x1, y1, x2, y2)
            if car_id in carPlate_dict:
                # retrieve car plate of current car from the car plate dictionary
                dict_license_plate_data = carPlate_dict[car_id][0]
                dict_license_plate, dict_license_plate_score = dict_license_plate_data

                licensePlate = dict_license_plate

                if dict_license_plate_score < license_plate_result[1]:
                    # update the car plate record to better precision car plate record
                    carPlate_dict.update({car_id: [(license_plate_result[0],license_plate_result[1])]})
                    # annotate the result to the frame
                    visualize(frame, score, license_plate_result[0], x1, y1, x2, y2)
                else:
                    # annotate the result to the frame
                    visualize(frame, score, dict_license_plate, x1, y1, x2,y2)
            else:
                if(car_id!=-1):
                    # save license plate recognition to car plate dictionary
                    if len(carPlate_dict) >= 10:
                        items = list(carPlate_dict.items())

                        # Remove the first item from the list
                        if items:
                            del items[0]
                        # Update the dictionary with the modified list
                        carPlate_dict = dict(items)
                    carPlate_dict[car_id] = [(license_plate_result[0], license_plate_result[1])]
                # annotate the result to the frame
                visualize(frame, score, license_plate_result[0], x1, y1, x2, y2)

            with open("resources/registered_car_plate.txt", 'r') as file:
                # Read all lines from the file
                lines = file.readlines()
                # Strip newline characters from each line and compare with the string value
                for line in lines:
                    if line.strip() == licensePlate:
                        authorizaiton_text = f"Authorized..."
                        cv2.putText(frame, authorizaiton_text, (0, 400), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                        with open("resources/entered_record.txt", "a") as file1:
                            if len(detected_license_plates) == 0:
                                detected_license_plates.append(licensePlate)
                                file1.write(f"Plate Number: {licensePlate} : Entered at {datetime.now()}" + "\n")
                            else:
                                if detected_license_plates[-1] != licensePlate:
                                    detected_license_plates.append(licensePlate)
                                    file1.write(
                                        f"Plate Number: {licensePlate} : Entered at {datetime.now()}" + "\n")


        cv2.imshow('RealTime license Plate System', frame)
        if cv2.waitKey(1) == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
