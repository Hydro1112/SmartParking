import cv2
import numpy as np
from ultralytics import YOLO
from utils.utils import get_car
from utils.readLicensePlate import readLicensePlate
from utils.utils import visualize
from sort.sort import Sort
from PIL import Image, ImageTk
import tkinter as tk
import datetime
import os

# Load models
mot_tracker = Sort()
coco_model = YOLO('models/yolov8n.pt')
license_plate_detector = YOLO('models/yolo/best.pt')

# Global variable to store the capture object
cap = None

def save_license_plate(license_plate_text, license_plate_score, car_id):
    """
    Save detected license plate to a text file with a timestamp.

    Args:
        license_plate_text (str): Detected license plate text.
        license_plate_score (float): Confidence score of the detection.
        car_id (int): ID of the car associated with the license plate.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("license_plates.txt", "a") as f:
        f.write(f"[{timestamp}] Car ID: {car_id}, License Plate: {license_plate_text}, Confidence: {license_plate_score:.2f}\n")

def yoloRealTimeModelDetect(frame_label, root, source=0):
    """
    Perform real-time license plate detection using YOLO and display results on a Tkinter label.

    Args:
        frame_label (tk.Label): Tkinter label to display the video feed.
        root (tk.Tk): Tkinter root window for scheduling updates.
        source: Camera index (e.g., 0 for webcam) or path to video file.
    """
    global cap
    if cap is not None:
        cap.release()  # Release any existing capture

    # Configure Camera or Video
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Error: Could not open source {source}")
        return
    cap.set(3, 640)
    cap.set(4, 480)
    vehicles = [2, 3, 5, 7]  # Vehicle class IDs
    threshold = 0.8
    carPlate_dict = {}  # Dictionary to store license plate data per car

    def update_frame():
        global cap
        if cap is None or not cap.isOpened():
            return

        ret, frame = cap.read()
        if not ret:
            cap.release()
            cap = None
            frame_label.config(image=ImageTk.PhotoImage(Image.new('RGB', (1, 1))))
            return

        # YOLO COCO pretrained model detection
        detections = coco_model(frame)[0]
        detections_ = []

        # Track vehicles
        for detection in detections.boxes.data.tolist():
            x1, y1, x2, y2, score, class_id = detection
            if int(class_id) in vehicles and score > threshold:
                detections_.append([x1, y1, x2, y2, score])

        # Update tracker
        detections_np = np.array(detections_).reshape(-1, 5)
        detections_bboxes = detections_np[:, :4]
        track_ids = mot_tracker.update(np.asarray(detections_bboxes))

        # Detect license plates
        license_plates = license_plate_detector(frame)[0]
        for license_plate in license_plates.boxes.data.tolist():
            x1, y1, x2, y2, score, class_id = license_plate
            if score > threshold:
                # Assign license plate to car
                xcar1, ycar1, xcar2, ycar2, car_id = get_car(license_plate, track_ids)
                if car_id != -1:
                    # Run license plate recognition
                    frame_copy = frame.copy()
                    license_plate_result = readLicensePlate(frame_copy, x1, y1, x2, y2)
                    license_plate_text, license_plate_score = license_plate_result

                    # Update carPlate_dict with higher confidence results
                    if car_id in carPlate_dict:
                        dict_license_plate, dict_license_plate_score = carPlate_dict[car_id][0]
                        if license_plate_score > dict_license_plate_score:
                            carPlate_dict[car_id] = [(license_plate_text, license_plate_score)]
                            save_license_plate(license_plate_text, license_plate_score, car_id)
                    else:
                        if len(carPlate_dict) >= 10:
                            carPlate_dict.pop(list(carPlate_dict.keys())[0])
                        carPlate_dict[car_id] = [(license_plate_text, license_plate_score)]
                        save_license_plate(license_plate_text, license_plate_score, car_id)

                    # Visualize the result on the frame
                    visualize(frame, license_plate_score, license_plate_text, x1, y1, x2, y2)

        # Convert frame to Tkinter-compatible format
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        img = img.resize((460, 460), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)

        # Update the Tkinter label
        frame_label.config(image=photo)
        frame_label.image = photo  # Keep a reference to prevent garbage collection

        # Schedule the next frame update
        root.after(10, update_frame)

    # Start the video processing loop
    update_frame()

    # Release the camera/video when the window is closed
    def on_closing():
        global cap
        if cap is not None:
            cap.release()
            cap = None
        root.quit()

    root.protocol("WM_DELETE_WINDOW", on_closing)

def stopCamera(frame_label, root):
    """
    Stop the camera or video feed and clear the display.

    Args:
        frame_label (tk.Label): Tkinter label displaying the video feed.
        root (tk.Tk): Tkinter root window.
    """
    global cap
    if cap is not None:
        cap.release()
        cap = None
    frame_label.config(image=ImageTk.PhotoImage(Image.new('RGB', (1, 1))))