import cv2
import re
import torch
import torch.nn.functional as F
from vietocr.tool.predictor import Predictor
from vietocr.tool.config import Cfg
from PIL import Image
import numpy as np # Thêm import numpy
from pathlib import Path

_predictor = None  # Biến global, lưu model VietOCR
PROJECT_ROOT = Path(__file__).resolve().parents[2]

def get_ocr():
    """
    Lazy initialization cho VietOCR, chỉ load model 1 lần duy nhất
    """
    global _predictor
    if _predictor is None:
        config = Cfg.load_config_from_name('vgg_transformer')
        config['weights'] = str(PROJECT_ROOT / 'server/models/transformerocr.pth')
        config['device'] = 'cuda' if torch.cuda.is_available() else 'cpu'
        _predictor = Predictor(config)
    return _predictor

def format_vn_plate(plate_text: str) -> str:
    """
    Chuẩn hoá biển số VN
    """
    plate_text = plate_text.strip().upper()
    plate_text = plate_text.replace(" ", "").replace("_", "-").replace(".", "")
    if "-" in plate_text:
        return plate_text
    m = re.match(r"^(\d{2}[A-Z]{1,2})(\d{4,5})$", plate_text)
    if m:
        return m.group(1) + "-" + m.group(2)
    return plate_text

def preprocess_for_ocr(plate_image: np.ndarray) -> np.ndarray:
    """
    Áp dụng các bước tiền xử lý để tăng chất lượng ảnh cho OCR.
    """
    # 1. Chuyển sang ảnh xám
    gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)

    # 2. Thay đổi kích thước (Resize) để có chiều cao cố định -> Tăng độ ổn định
    # Chiều cao 64px thường cho kết quả tốt với OCR
    TARGET_HEIGHT = 64
    height, width = gray.shape
    scale = TARGET_HEIGHT / height
    new_width = int(width * scale)
    resized = cv2.resize(gray, (new_width, TARGET_HEIGHT), interpolation=cv2.INTER_CUBIC)

    # 3. Áp dụng CLAHE (Contrast Limited Adaptive Histogram Equalization)
    # Kỹ thuật này rất hiệu quả trong việc làm rõ các chi tiết trong điều kiện ánh sáng không đồng đều.
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(resized)

    return enhanced


def readLicensePlate(img, x1, y1, x2, y2):
    """
    Cắt ảnh, tiền xử lý và OCR biển số bằng VietOCR
    Trả về [plate_text, confidence]
    """
    h, w = img.shape[:2]
    # Mở rộng bounding box một chút để đảm bảo không mất ký tự
    newx1 = max(int(x1 - 3), 0)
    newy1 = max(int(y1 - 3), 0)
    newx2 = min(int(x2 + 3), w)
    newy2 = min(int(y2 + 3), h)

    license_plate_crop = img[newy1:newy2, newx1:newx2]
    
    if license_plate_crop.size == 0:
        return ["", 0.0]

    # <<<<<<<<<<<<<<< ÁP DỤNG TIỀN XỬ LÝ TẠI ĐÂY >>>>>>>>>>>>>>>
    processed_plate = preprocess_for_ocr(license_plate_crop)

    # Convert ảnh đã xử lý (numpy array) -> PIL Image
    license_plate_pil = Image.fromarray(processed_plate)

    predictor = get_ocr()

    plate_text = ""
    confidence = 0.0
    try:
        # Lấy text
        plate_text = predictor.predict(license_plate_pil)

        # Lấy confidence gần đúng từ logits
        raw_logits = predictor.predict_raw(license_plate_pil)
        probs = [F.softmax(logit, dim=-1) for logit in raw_logits]
        max_probs = [p.max().item() for p in probs]
        
        # Thay vì nhân, dùng trung bình cộng để tránh bị "phạt" quá nặng khi biển số dài
        if max_probs:
            confidence = float(np.mean(max_probs))
        else:
            confidence = 0.0

    except Exception:
        confidence = 0.0  # fallback

    # Làm sạch & chuẩn hóa format
    plate_text = re.sub(r"[^A-Z0-9]", "", plate_text.upper())
    plate_text = format_vn_plate(plate_text)

    return [plate_text, confidence]
