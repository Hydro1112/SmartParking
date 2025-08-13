import easyocr
import cv2
import re

reader = easyocr.Reader(['en'], gpu=True)

def format_vn_plate(plate_text):
    """
    Chuẩn hoá biển số VN:
    - Nếu có dạng 2 số + 1 chữ cái + (4-5 số) và không có '-', thêm '-'
    """
    if '-' in plate_text:
        return plate_text
    m = re.match(r"^(\d{2}[A-Z]{1,2})(\d{4,5})$", plate_text)
    if m:
        return m.group(1) + "-" + m.group(2)
    return plate_text

def readLicensePlate(img, x1, y1, x2, y2):
    # Crop license plate
    h, w = img.shape[:2]
    newx1 = max(int(x1 - 3), 0)
    newy1 = max(int(y1 - 3), 0)
    newx2 = min(int(x2 + 3), w)
    newy2 = min(int(y2 + 3), h)

    license_plate_crop = img[newy1:newy2, newx1:newx2]
    license_plate_crop_gray = cv2.cvtColor(license_plate_crop, cv2.COLOR_BGR2GRAY)
    license_plate_inverted = cv2.bitwise_not(license_plate_crop_gray)

    # OCR
    license_plate_detections = reader.readtext(license_plate_inverted)
    if not license_plate_detections:
        return ["", 0.0]

    # Sắp xếp theo toạ độ Y (top-left)
    license_plate_detections.sort(key=lambda det: det[0][0][1])

    lines = []
    for bbox, texts, score in license_plate_detections:
        texts = texts.upper().replace(' ', '')
        # Loại ký tự không hợp lệ
        texts = re.sub(r'[^A-Z0-9]', '', texts)
        if texts:
            lines.append((texts, score))

    if not lines:
        return ["", 0.0]

    # Ghép 1 hoặc 2 dòng
    if len(lines) == 1:
        plate_text = lines[0][0]
        confScore = lines[0][1]
    else:
        plate_text = lines[0][0] + "-" + lines[1][0]
        confScore = (lines[0][1] + lines[1][1]) / 2

    # Format chuẩn biển VN nếu cần
    plate_text = format_vn_plate(plate_text)

    # Validate
    if plate_text and not plate_text[0].isdigit() and not plate_text[0].isalpha():
        return ["", 0.0]

    return [plate_text, confScore]
