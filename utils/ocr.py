import os
import sys
import re
import numpy as np
import cv2
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from pdf2image import convert_from_path

# =====================================================================
# SYSTEM CONFIGURATION INJECTION SECTION (WINDOWS DIRECT PATH GUARDS)
# =====================================================================
TESSERACT_EXE_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_EXE_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE_PATH

POPPLER_BIN_DIR = r"C:\Users\KIIT\Downloads\Release-26.02.0-0\poppler-26.02.0\Library\bin"


# =====================================================================


def fix_image_orientation(image_np: np.ndarray) -> np.ndarray:
    """Uses Tesseract OSD metadata properties to rotate tilted or upside-down

    document images upright.
    """
    try:
        # Step 1: Run Orientation and Script Detection (PSM 0)
        osd_meta = pytesseract.image_to_osd(image_np)

        # Isolate the exact rotation degree parameter using regex matching
        rotation_match = re.search(r'Rotate:\s*(\d+)', osd_meta)
        if rotation_match:
            angle = int(rotation_match.group(1))
            print(f"[OCR Orientation Guard] Detected document rotation: {angle}° degrees clockwise.", file=sys.stderr)

            # Step 2: Rotate the image matrix back to an upright position
            if angle == 90:
                return cv2.rotate(image_np, cv2.ROTATE_90_CLOCKWISE)
            elif angle == 180:
                return cv2.rotate(image_np, cv2.ROTATE_180)
            elif angle == 270:
                return cv2.rotate(image_np, cv2.ROTATE_90_COUNTERCLOCKWISE)
    except Exception as osd_error:
        # If the page layout is too sparse to calculate orientation metrics, pass it through safely
        print(f"[OCR Orientation Guard] OSD calculation skipped: {osd_error}", file=sys.stderr)

    return image_np


def preprocess_image_matrix(image_np: np.ndarray) -> np.ndarray:
    """Applies an advanced adaptive threshold pipeline to flatten backgrounds."""
    gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)

    # Smooth out camera grain noise while keeping text edges intact
    denoised_faint = cv2.bilateralFilter(gray, d=11, sigmaColor=85, sigmaSpace=85)

    # Adaptive Thresholding handles localized illumination shifts
    adaptive_thresh = cv2.adaptiveThreshold(
        denoised_faint,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=15
    )

    # Morphological Opening deletes loose hanging pixel specs
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    return cv2.morphologyEx(adaptive_thresh, cv2.MORPH_OPEN, kernel)


def extract_text_with_ocr(pdf_path: str) -> str:
    """Converts scanned PDF tracks into uncompressed 300 DPI matrices, fixes orientation,

    and runs character extraction passes.
    """
    if not pdf_path or not os.path.exists(pdf_path):
        return ""

    pages = []
    try:
        if os.path.exists(POPPLER_BIN_DIR):
            pages = convert_from_path(str(pdf_path), dpi=300, poppler_path=POPPLER_BIN_DIR)
        else:
            pages = convert_from_path(str(pdf_path), dpi=300)
    except Exception as error:
        print(f"[OCR Critical] Poppler transformation layer failed: {error}", file=sys.stderr)
        try:
            fallback_text = ""
            with fitz.open(str(pdf_path)) as doc:
                for page in doc:
                    fallback_text += page.get_text()
            return fallback_text
        except Exception:
            return ""

    ocr_text_pool = []

    for page_idx, page_image in enumerate(pages, start=1):
        try:
            img_np = cv2.cvtColor(np.array(page_image), cv2.COLOR_RGB2BGR)

            # Step 1: Detect orientation and rotate image upright
            oriented_matrix = fix_image_orientation(img_np)

            # Step 2: Run cleaning and denoising parameters
            optimized_matrix = preprocess_image_matrix(oriented_matrix)

            # Step 3: Extract text using Sparse Grid processing optimized for tabular alignments
            # --psm 11 looks for sparse text layouts and tables, preserving column alignments
            grid_config = "--psm 11 -c preserve_interword_spaces=1"
            page_text_token = pytesseract.image_to_string(optimized_matrix, config=grid_config)

            # Fallback pass: Try a more structured page layout analysis if extraction is too sparse
            if not page_text_token.strip() or len(page_text_token.strip()) < 50:
                raw_gray = cv2.cvtColor(oriented_matrix, cv2.COLOR_BGR2GRAY)
                page_text_token = pytesseract.image_to_string(raw_gray, config="--psm 3 -c preserve_interword_spaces=1")
            if page_text_token.strip():
                ocr_text_pool.append(page_text_token)

        except Exception as page_error:
            print(f"[OCR Warning] Layout extraction crashed on page {page_idx}: {page_error}", file=sys.stderr)
            continue

    return "\n\n".join(ocr_text_pool)


# =====================================================================
# EXPLICIT FUNCTION EXPOSURE COUPLING GUARDS
# =====================================================================
# This ensures that whether parser.py calls 'extract_text' OR
# 'extract_text_with_ocr', it will execute perfectly every time!
extract_text = extract_text_with_ocr