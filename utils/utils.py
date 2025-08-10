import cv2
import numpy as np

def visualize(img, license_plateScore, license_plate, pointx1, pointy1, pointx2, pointy2):
    """
    Draw a rectangle around the license plate and display the license plate text with confidence score.

    Args:
        img: Input image (numpy array, BGR format).
        license_plateScore (float): Confidence score of the license plate detection.
        license_plate (str): Detected license plate text.
        pointx1, pointy1, pointx2, pointy2 (float): Coordinates of the license plate bounding box.
    """
    # Check if image is valid
    if img is None or img.size == 0:
        print("Invalid image provided to visualize")
        return

    # Ensure coordinates are within image bounds
    height, width = img.shape[:2]
    x1 = max(0, int(pointx1))
    y1 = max(0, int(pointy1))
    x2 = min(width, int(pointx2))
    y2 = min(height, int(pointy2))

    # Create label with confidence score and license plate text
    label = f"{int(license_plateScore * 100)}% {license_plate}"

    # Draw rectangle around license plate
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

    # Adjust text position to avoid going out of image bounds
    text_y = max(10, y1 - 10)  # Ensure text is not above the image
    cv2.putText(img, label, (x1, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

def get_car(license_plate, vehicle_track_ids):
    """
    Retrieve the vehicle coordinates and ID based on the license plate coordinates.

    Args:
        license_plate (tuple): Tuple containing the coordinates of the license plate (x1, y1, x2, y2, score, class_id).
        vehicle_track_ids (list): List of vehicle track IDs and their corresponding coordinates.

    Returns:
        tuple: Tuple containing the vehicle coordinates (x1, y1, x2, y2) and ID, or (-1, -1, -1, -1, -1) if not found.
    """
    # Validate inputs
    if not isinstance(license_plate, (tuple, list)) or len(license_plate) != 6:
        print("Invalid license plate data")
        return -1, -1, -1, -1, -1
    if not vehicle_track_ids:
        print("Empty vehicle track IDs list")
        return -1, -1, -1, -1, -1

    x1, y1, x2, y2, _, _ = license_plate

    # Find vehicle that contains the license plate
    for vehicle in vehicle_track_ids:
        if len(vehicle) != 5:
            continue
        xcar1, ycar1, xcar2, ycar2, car_id = vehicle
        if x1 > xcar1 and y1 > ycar1 and x2 < xcar2 and y2 < ycar2:
            return vehicle

    return -1, -1, -1, -1, -1