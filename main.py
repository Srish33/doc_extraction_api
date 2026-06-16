import json
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile, Request, Header, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from utils.formatter import format_response
from utils.extractor import extract_text_from_pdf

load_dotenv()

app = FastAPI(title="PDF to JSON Extraction API")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RawTextPayload(BaseModel):
    text: str
    keyword: Optional[str] = None


def save_and_log_metadata(filename: str, content_type: str, binary_content: bytes, raw_text: str) -> dict:
    if not binary_content and content_type != "text/plain":
        raise HTTPException(status_code=400, detail="Empty file stream cannot be logged.")

    size_bytes = len(binary_content)

    if binary_content:
        saved_file_path = UPLOAD_DIR / filename
        with open(saved_file_path, "wb") as f:
            f.write(binary_content)

    metadata_payload = {
        "filename": filename,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "content_text": raw_text
    }

    metadata_filename = f"{Path(filename).stem}_metadata.json"
    metadata_file_path = UPLOAD_DIR / metadata_filename
    with open(metadata_file_path, "w", encoding="utf-8") as json_f:
        json.dump(metadata_payload, json_f, indent=4)

    print(f"[Storage Matrix Engine] Successfully written tracking metadata for: {filename}", flush=True)
    return metadata_payload


@app.post("/upload")
async def upload_multipart_form(
        file: UploadFile = File(...),
        keyword: Optional[str] = Form(None)
):
    file_content = await file.read()

    unique_prefix = uuid4().hex[:8]
    temp_filename = f"{unique_prefix}_{file.filename}"
    temp_path = UPLOAD_DIR / temp_filename

    with open(temp_path, "wb") as f:
        f.write(file_content)

    try:
        extracted_text = extract_text_from_pdf(str(temp_path))
    except Exception as e:
        extracted_text = file_content.decode("utf-8", errors="ignore")

    save_and_log_metadata(
        filename=file.filename,
        content_type=file.content_type or "application/pdf",
        binary_content=file_content,
        raw_text=extracted_text
    )

    try:
        return format_response(file.filename, extracted_text, search_keyword=keyword)
    finally:
        if temp_path.exists():
            temp_path.unlink()


@app.post("/upload/raw-bytes")
async def upload_raw_binary_pdf(
        request: Request,
        q: Optional[str] = None,
        x_file_name: Optional[str] = Header(None)
):
    body_bytes = await request.body()
    if not body_bytes:
        raise HTTPException(status_code=400, detail="The raw body payload is empty.")

    original_filename = x_file_name if x_file_name else f"raw_stream_{uuid4().hex[:6]}.pdf"
    file_path = UPLOAD_DIR / original_filename

    try:
        file_path.write_bytes(body_bytes)
        extracted_text = extract_text_from_pdf(str(file_path))

        save_and_log_metadata(
            filename=original_filename,
            content_type="application/pdf",
            binary_content=body_bytes,
            raw_text=extracted_text
        )

        return format_response(original_filename, extracted_text, search_keyword=q)

    except Exception as err:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=str(err))


@app.post("/upload/raw-text")
async def upload_raw_text(payload: RawTextPayload):
    extracted_text = payload.text
    search_keyword = payload.keyword

    if not extracted_text.strip():
        raise HTTPException(status_code=400, detail="The 'text' field inside the body payload is empty.")

    filename = f"text_stream_{uuid4().hex[:6]}.txt"
    raw_text_bytes = extracted_text.encode("utf-8")

    save_and_log_metadata(
        filename=filename,
        content_type="text/plain",
        binary_content=raw_text_bytes,
        raw_text=extracted_text
    )

    return format_response(filename, extracted_text, search_keyword=search_keyword)