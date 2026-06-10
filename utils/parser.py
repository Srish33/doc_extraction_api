import os
from typing import Dict, Any

from . import extractor
from . import ocr as ocr_mod
from . import formatter as formatter_mod


def process_document(pdf_path: str, filename: str = None, search_keyword: str = None) -> Dict[str, Any]:
    """Orchestrates document intelligence execution. Safely routes native digital text

    layers, falling back to OCR only if no usable contents populate.
    """
    if filename is None:
        filename = os.path.basename(pdf_path)

    # Step 1: Run native text extraction sweep
    try:
        text = extractor.extract_text_from_pdf(pdf_path)
    except Exception:
        text = ""

    # Validate output viability using structural metrics
    clean_check = text.strip() if text else ""

    # Step 2: Fallback trigger condition check
    # If the file returns no native layout characters, invoke Tesseract
    if not clean_check or len(clean_check) < 15:
        print("[Parser Dispatch] Empty native layer or scan verified. Invoking Image OCR Matrix...", flush=True)
        text = ocr_mod.extract_text_with_ocr(pdf_path)
    else:
        print(
            f"[Parser] Active native text layer identified ({len(clean_check)} characters). Bypassing Image OCR loop.",
            flush=True)

    # Step 3: Call the pristine layout-compliant formatter
    response = formatter_mod.format_response(filename, text=text, search_keyword=search_keyword)
    return response
