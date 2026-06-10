try:
    import pymupdf as fitz
except ImportError:
    import fitz


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts layout text blocks cleanly from a digital PDF layer."""
    try:
        with fitz.open(pdf_path) as document:
            if document.page_count == 0:
                raise ValueError("The PDF does not contain any pages.")

            page_text = []
            for page in document:
                # Extracts raw sequential layout streams natively
                text = page.get_text("text")
                page_text.append(text)

            return "\n".join(page_text)

    except ValueError:
        raise
    except fitz.FileDataError as error:
        raise ValueError("The uploaded file is not a valid PDF.") from error
    except Exception as error:
        raise RuntimeError(f"PDF extraction failed: {error}") from error