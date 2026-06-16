import os
import re
import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path

TESSERACT_EXE_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_EXE_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE_PATH


def fix_image_orientation(image_np: np.ndarray) -> np.ndarray:
    try:
        if image_np.shape[0] < 100 or image_np.shape[1] < 100:
            return image_np
        osd_meta = pytesseract.image_to_osd(image_np)
        rotation_match = re.search(r'Rotate:\s*(\d+)', osd_meta)
        if rotation_match:
            angle = int(rotation_match.group(1))
            if angle == 90:
                return cv2.rotate(image_np, cv2.ROTATE_90_CLOCKWISE)
            elif angle == 180:
                return cv2.rotate(image_np, cv2.ROTATE_180)
            elif angle == 270:
                return cv2.rotate(image_np, cv2.ROTATE_90_COUNTERCLOCKWISE)
    except Exception as ocr_warn:
        print(f"[OCR Window Warning] Orientation check skipped: {ocr_warn}", flush=True)
    return image_np


def preprocess_image_matrix(image_np: np.ndarray) -> np.ndarray:
    """
    Advanced preprocessing for multi-column grids.
    Uses rescaling, Otsu binarization, and morphological cleanup
    to stop text lines from turning into broken gibberish.
    """
    # 1. Convert to grayscale and rescale up to enhance small text characters
    gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)

    # 2. Denoise lightly while keeping text edges crisp
    denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)

    # 3. Apply Otsu's threshold combined with Gaussian filtering for clean text backgrounds
    blurred = cv2.GaussianBlur(denoised, (3, 3), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 4. Remove small noise specs and line fragments that disrupt string layouts
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    return cleaned


def extract_text_with_ocr(pdf_path: str) -> str:
    """
    Converts multi-paged semester records into high-contrast frames and
    extracts string layers using PSM 11 to track structured grid records.
    """
    if not pdf_path or not os.path.exists(pdf_path):
        return ""

    try:
        local_poppler = os.path.join(os.getcwd(), "poppler-windows", "bin")
        if not os.path.exists(local_poppler):
            local_poppler = r"C:\Program Files\poppler-windows\Library\bin"

        pages = convert_from_path(str(pdf_path), dpi=300,
                                  poppler_path=local_poppler if os.path.exists(local_poppler) else None)
    except Exception as e:
        print(f"[OCR Error] Poppler failed to render pages: {e}", flush=True)
        return ""

    ocr_text_pool = []
    for page_image in pages:
        img_np = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)
        oriented = fix_image_orientation(img_np)
        optimized = preprocess_image_matrix(oriented)

        layout_config = "--psm 11 -c preserve_interword_spaces=1"
        full_text = pytesseract.image_to_string(optimized, config=layout_config)

        if full_text.strip():
            ocr_text_pool.append(full_text.strip())

    return "\n\n".join(ocr_text_pool)