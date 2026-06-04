import pytesseract
from pdf2image import convert_from_path


def extract_text_with_ocr(pdf_path):
    """Extract text from scanned/image PDFs using Tesseract OCR."""
    try:
        images = convert_from_path(pdf_path)
    except Exception as error:
        raise RuntimeError(f"Could not convert PDF pages for OCR: {error}") from error

    if not images:
        return ""

    try:
        ocr_text = []
        for image in images:
            ocr_text.append(pytesseract.image_to_string(image))
        return "\n".join(ocr_text)
    except pytesseract.TesseractNotFoundError as error:
        raise RuntimeError(
            "Tesseract OCR is not installed or is not available in PATH."
        ) from error
    except Exception as error:
        raise RuntimeError(f"OCR extraction failed: {error}") from error
