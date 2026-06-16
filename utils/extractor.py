import os
from pypdf import PdfReader

TESSERACT_EXE_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(TESSERACT_EXE_PATH):
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_EXE_PATH

def extract_text_from_pdf(file_path: str) -> str:
    text = ""
    try:
        reader = PdfReader(file_path)
        text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    except Exception as e:
        print(f"[Extractor Layer] Structural read failed: {e}")

    if not text.strip():
        print(f"[Extractor Layer] Scanned document profile detected. Initializing OCR matrix...", flush=True)
        try:
            from utils.ocr import extract_text_with_ocr
            text = extract_text_with_ocr(file_path)
        except Exception as ocr_err:
            print(f"[Critical Extractor Failure] Local OCR chain halted: {ocr_err}")
            text = ""

    return text