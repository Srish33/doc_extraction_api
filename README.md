# PDF to JSON Extraction API

FastAPI backend for uploading PDF files, extracting readable text, using OCR
for scanned PDFs, and returning a structured JSON response.

## Features

- `GET /` health check
- `POST /upload` PDF upload endpoint
- Text extraction for normal PDFs with PyMuPDF
- OCR fallback for scanned/image PDFs with `pdf2image` and `pytesseract`
- Multi-page document support
- Clean JSON response formatting
- Modular utility files for extraction, OCR, parsing, and formatting

## Project Structure

```text
project_root/
|-- main.py
|-- requirements.txt
|-- README.md
|-- uploads/
|-- utils/
|   |-- __init__.py
|   |-- extractor.py
|   |-- ocr.py
|   |-- parser.py
|   `-- formatter.py
`-- tests/
```

## Setup

Install Python dependencies:

```bash
pip install -r requirements.txt
```

OCR also requires system tools:

- Install Tesseract OCR and make sure `tesseract` is available in `PATH`.
- Install Poppler and make sure its `bin` directory is available in `PATH`.

On Windows, if OCR fails, check that both tools can be run from a terminal.

## Run

```bash
uvicorn main:app --reload
```

Open Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## API

### `GET /`

Returns:

```json
{
  "message": "Backend is running"
}
```

### `POST /upload`

Send `multipart/form-data` with field name `file`.

Example response:

```json
{
  "filename": "sample.pdf",
  "document_type": "Receipt",
  "important_details_heading": "Important Details",
  "important_details": {
    "title": "Receipt",
    "receipt_number": "123",
    "date_paid": "March 25, 2024",
    "payment_method": "ACH",
    "total": "$20.12",
    "tables": [
      {
        "headers": ["description", "unit_cost", "quantity", "amount"],
        "rows": [
          ["Subscription", "$19.00", "1", "$19.00"]
        ],
        "arrow_rows": [
          "description -> Subscription | unit_cost -> $19.00 | quantity -> 1 | amount -> $19.00"
        ]
      }
    ]
  },
  "document_preview_heading": "Document Preview",
  "document_preview": "Title: Receipt. Receipt Number: 123. Date Paid: March 25, 2024. Total: $20.12. Tables: Headers: description; unit_cost; quantity; amount, Rows: Subscription; $19.00; 1; $19.00, Arrow Rows: description -> Subscription | unit_cost -> $19.00 | quantity -> 1 | amount -> $19.00"
}
```

For non-receipt PDFs with tables, the same table structure is returned:

```json
{
  "filename": "report.pdf",
  "document_type": "Report",
  "important_details_heading": "Important Details",
  "important_details": {
    "title": "Sales Report",
    "tables": [
      {
        "headers": ["Item", "Quantity", "Amount"],
        "rows": [
          ["Pen", "3", "6"],
          ["Book", "2", "10"]
        ],
        "arrow_rows": [
          "Item -> Pen | Quantity -> 3 | Amount -> 6",
          "Item -> Book | Quantity -> 2 | Amount -> 10"
        ]
      }
    ]
  },
  "document_preview_heading": "Document Preview",
  "document_preview": "Title: Sales Report. Tables: Headers: Item; Quantity; Amount, Rows: Pen; 3; 6; Book; 2; 10, Arrow Rows: Item -> Pen | Quantity -> 3 | Amount -> 6; Item -> Book | Quantity -> 2 | Amount -> 10"
}
```

## Notes

OCR runs only when normal PDF text extraction returns empty text. The modular
structure leaves room for future NLP, table extraction, summarization, database
storage, or cloud deployment.
