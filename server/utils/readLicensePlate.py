import cv2
import re
import torch
import torch.nn.functional as F
from vietocr.tool.predictor import Predictor
from vietocr.tool.config import Cfg
from PIL import Image

_predictor = None  # Biến global, lưu model VietOCR

def get_ocr():
    """
    Lazy initialization cho VietOCR, chỉ load model 1 lần duy nhất
    """
    global _predictor
    if _predictor is None:
        config = Cfg.load_config_from_name('vgg_transformer')
        config['weights'] = 'server/models/transformerocr.pth'  # đường dẫn model đã train
        config['device'] = 'cuda'  # hoặc 'cpu' nếu không có GPU
        _predictor = Predictor(config)
    return _predictor


def format_vn_plate(plate_text: str) -> str:
    """
    Chuẩn hoá biển số VN:
    - Nếu có dạng 2 số + 1-2 chữ cái + (4-5 số) và không có '-', thêm '-'
    """
    plate_text = plate_text.strip().upper()
    plate_text = plate_text.replace(" ", "").replace("_", "-")
    if "-" in plate_text:
        return plate_text
    m = re.match(r"^(\d{2}[A-Z]{1,2})(\d{4,5})$", plate_text)
    if m:
        return m.group(1) + "-" + m.group(2)
    return plate_text


def readLicensePlate(img, x1, y1, x2, y2):
    """
    Cắt ảnh theo toạ độ và OCR biển số bằng VietOCR
    Trả về [plate_text, confidence]
    """
    h, w = img.shape[:2]
    newx1 = max(int(x1 - 3), 0)
    newy1 = max(int(y1 - 3), 0)
    newx2 = min(int(x2 + 3), w)
    newy2 = min(int(y2 + 3), h)

    license_plate_crop = img[newy1:newy2, newx1:newx2]

    # Convert OpenCV (BGR numpy array) -> PIL (RGB)
    license_plate_crop_rgb = cv2.cvtColor(license_plate_crop, cv2.COLOR_BGR2RGB)
    license_plate_pil = Image.fromarray(license_plate_crop_rgb)

    predictor = get_ocr()

    # Lấy text
    plate_text = predictor.predict(license_plate_pil)

    # Lấy confidence gần đúng từ logits
    try:
        raw_logits = predictor.predict_raw(license_plate_pil)  # List[Tensor]
        probs = [F.softmax(logit, dim=-1) for logit in raw_logits]
        max_probs = [p.max().item() for p in probs]
        confidence = float(torch.tensor(max_probs).prod())
    except Exception:
        confidence = 0.0  # fallback nếu predict_raw không thành công

    # Làm sạch & chuẩn hóa format
    plate_text = re.sub(r"[^A-Z0-9]", "", plate_text.upper())
    plate_text = format_vn_plate(plate_text)

    return [plate_text, confidence]
