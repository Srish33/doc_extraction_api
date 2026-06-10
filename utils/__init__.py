"""Utility subpackage for the PDF-to-JSON service.

This package contains small, focused modules:
- extractor.py: extract embedded text from PDFs using PyMuPDF
- ocr.py: convert PDF pages to images and run Tesseract OCR
- parser.py: lightweight text normalisation utilities
- formatter.py: heuristics to convert raw text into structured JSON

Modules expose simple helper functions that are imported by `main.py`.
"""
