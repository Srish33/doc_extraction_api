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
|-- index.html
|-- Dockerfile
|-- docker-compose.yml
|-- .dockerignore
|-- requirements.txt
|-- README.md
|-- uploads/
`-- utils/
    |-- __init__.py
    |-- extractor.py
    |-- ocr.py
    |-- parser.py
    `-- formatter.py
```

## Setup

Install Python dependencies:

```bash
pip install -r requirements.txt
```

OCR also requires system tools:

- Install Tesseract OCR and make sure `tesseract` is available in `PA       TH`.
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

## Docker Setup (Alternative Containerized Workflow)
This entire application infrastructure can also be executed inside isolated virtual environments using Docker Desktop. When running via Docker, you do not need to manually install Python, Tesseract OCR, or Poppler binaries locally on your host Windows operating system.

## Prerequisites
Ensure you have downloaded and installed Docker Desktop (configured with the WSL 2 backend engine) running on your standard 64-bit AMD64/x86_64 host machine.

## Execution
Open your project terminal console window workspace.
Initialize and deploy the automated background service network container stack by executing:

```bash
docker compose up --build -d
```
Confirm that your service container nodes are online and running cleanly:

```bash
docker compose ps
```

## Application Network Architecture (Docker)
Once compilation cycles wrap up successfully, you can instantly interact with the production endpoints using these local host network connections:

Web UI Dashboard (Nginx Server): http://localhost:8080

Interactive Backend API Docs (FastAPI Swagger UI): http://localhost:8000/docs

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


  "message": "Backend is running"
}
### `POST /upload`
Send `multipart/form-data` with field name `file`.

Operations and Pipeline Maintenance (Docker)
Live Tracking Logs
To inspect real-time console prints, image pre-processing warnings, or metadata file generation events inside your core API machine layer:

```bash
docker compose logs -f api-backend
```

## Shutting Down Services
To spin down your container clusters, clear local network allocations, and free up system memory when your working session wraps up:

```bash
docker compose down
```

## Notes

OCR runs only when normal PDF text extraction returns empty text. The modular
structure leaves room for future NLP, table extraction, summarization, database
storage, or cloud deployment.
