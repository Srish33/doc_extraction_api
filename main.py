from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile

from utils.extractor import extract_text_from_pdf
from utils.formatter import format_response
from utils.ocr import extract_text_with_ocr
from utils.parser import clean_text

app = FastAPI(
    title="PDF to JSON Extraction API",
    description="Upload PDF files, extract readable text, and return structured JSON.",
    version="1.0.0",
)

UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)


@app.get("/")
def home():
    return {"message": "Backend is running"}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file was uploaded.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Prefix the original name so repeated uploads do not overwrite old files.
    safe_filename = Path(file.filename).name
    saved_filename = f"{uuid4().hex}_{safe_filename}"
    file_path = UPLOAD_FOLDER / saved_filename

    try:
        file_path.write_bytes(contents)
    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not save uploaded file: {error}",
        ) from error

    try:
        extracted_text = extract_text_from_pdf(file_path)

        # Scanned PDFs usually return no embedded text, so OCR is the fallback.
        if not extracted_text.strip():
            extracted_text = extract_text_with_ocr(file_path)

        cleaned_text = clean_text(extracted_text)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    return format_response(
        filename=file.filename,
        text=cleaned_text,
    )
