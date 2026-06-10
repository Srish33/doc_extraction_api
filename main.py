import os
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware

from utils.formatter import format_response
from utils.parser import process_document

app = FastAPI(title="Core Document Intelligence API", version="1.0.0")

# =====================================================================
# 🔥 ADD CORS MIDDLEWARE GUARD TO ENABLE BROWSER CONNECTION
# =====================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Authorizes all browser ports to interface with routes
    allow_credentials=True,
    allow_methods=["*"],  # Permits standard POST, GET requests
    allow_headers=["*"],
)
# =====================================================================

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True, parents=True)



@app.get("/")
async def root_index():
    """Health check endpoint - confirms API is running."""
    return {
        "status": "online",
        "message": "Document Intelligence API is running. Use the POST /upload endpoint to process PDFs."
    }


@app.post("/upload")
async def upload_pdf_document(file: UploadFile = File(...), keyword: str = Form(None)):
    """Upload and process PDF/PNG documents.
    
    Accepts PDF or PNG files, extracts text using native extraction or OCR fallback,
    and returns structured JSON with document intelligence.
    
    Args:
        file: PDF or PNG file to process
        keyword: Optional search keyword to find matches in document text
    
    Returns:
        JSON response with extracted document details and keyword matches
    """
    if not file.filename.lower().endswith(".pdf") and not file.filename.lower().endswith(".png"):
        raise HTTPException(status_code=400, detail="Unsupported file format.")

    contents = await file.read()
    unique_name = f"{uuid4().hex[:8]}_{file.filename.replace(' ', '_')}"
    file_path = UPLOAD_DIR / unique_name
    file_path.write_bytes(contents)

    try:
        # FIXED: Forward the keyword parameter straight to the orchestrator layer
        response = process_document(str(file_path), filename=file.filename, search_keyword=keyword)
        return response
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@app.post("/upload/raw-bytes")
async def upload_raw_bytes_document(request: Request, filename: str = "raw_stream.pdf"):
    """Accepts raw binary data stream directly from Postman request body.
    
    Processes the binary payload through the structured JSON intelligence pipeline,
    supporting any binary-compatible format (PDF, images, etc.).
    
    Args:
        request: HTTP request with raw binary body
        filename: Name to assign to the uploaded file
    
    Returns:
        JSON response with extracted document details
    """
    # 1. Read the entire raw body payload directly from the network stream
    body_bytes = await request.body()

    if not body_bytes:
        raise HTTPException(status_code=400, detail="The request body stream is empty.")

    # 2. Save the raw binary buffer into a temporary file asset path
    unique_name = f"{uuid4().hex[:8]}_{filename}"
    file_path = UPLOAD_DIR / unique_name

    try:
        file_path.write_bytes(body_bytes)

        # 3. Forward the file path straight to your central orchestrator pipeline
        response = process_document(str(file_path), filename=filename)
        return response

    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        # 4. Clean up the disk asset immediately after formatting
        if os.path.exists(file_path):
            os.remove(file_path)


# NEW TARGET ROUTE: Explicitly processes raw body text entries pasted into Postman
@app.post("/upload/raw-text")
async def upload_raw_text_body(request: Request, keyword: str = None):
    """Reads unformatted text pasted directly into Postman 'raw' text body.
    
    Extracts text content from request body and outputs a perfectly formatted
    JSON response array with document intelligence.
    
    Args:
        request: HTTP request with raw text body
        keyword: Optional search keyword to find matches in the text
    
    Returns:
        JSON response with formatted text analysis and keyword matches
    """
    # 1. Extract raw byte stream from the body payload
    body_bytes = await request.body()
    if not body_bytes:
        raise HTTPException(status_code=400, detail="The raw body field is empty. Please paste text in Postman.")

    try:
        # 2. Decode the incoming bytes smoothly into a Python string block
        raw_text_content = body_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Invalid text encoding layout. Must be UTF-8 string format.")

    try:
        print(f"[Parser Raw Stream] Received raw data payload string ({len(raw_text_content)} characters).", flush=True)

        # 3. Bypass file saving and pass the string straight to your high-precision formatter
        response = format_response(filename="raw_input_text.txt", text=raw_text_content, search_keyword=keyword)
        return response
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))