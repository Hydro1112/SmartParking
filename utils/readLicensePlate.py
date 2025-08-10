import easyocr
import cv2
import numpy as np

reader = easyocr.Reader(['en'], gpu=True)

def readLicensePlate(img, x1, y1, x2, y2):
    # Ensure coordinates are within image bounds
    height, width = img.shape[:2]
    x1 = max(0, int(x1 - 3))
    y1 = max(0, int(y1 - 3))
    x2 = min(width, int(x2 + 3))
    y2 = min(height, int(y2 + 3))

    # Check if the cropped region is valid
    if x2 <= x1 or y2 <= y1:
        return ["", 0.0]

    # Crop out the license plate
    license_plate_crop = img[y1:y2, x1:x2]

    # Check if cropped image is valid
    if license_plate_crop.size == 0:
        return ["", 0.0]

    # Process license plate
    license_plate_crop_gray = cv2.cvtColor(license_plate_crop, cv2.COLOR_BGR2GRAY)
    license_plate_inverted = cv2.bitwise_not(license_plate_crop_gray)

    # Run EasyOCR
    license_plate_detections = reader.readtext(license_plate_inverted)
    
    if not license_plate_detections:
        return ["", 0.0]

    # Process detections
    license_plate_text = ""
    total_score = 0.0
    num_detections = 0

    for detection in license_plate_detections:
        _, text, score = detection
        text = text.upper().replace(" ", "")  # Normalize text
        # Only include alphanumeric characters
        cleaned_text = "".join(char for char in text if char.isalnum())
        if cleaned_text:
            license_plate_text += cleaned_text
            total_score += score
            num_detections += 1

    # Calculate average confidence score
    conf_score = total_score / num_detections if num_detections > 0 else 0.0

    return [license_plate_text, conf_score]