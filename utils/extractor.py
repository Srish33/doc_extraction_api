try:
    import pymupdf as fitz
except ImportError:
    import fitz


def extract_text_from_pdf(pdf_path):
    """Extract embedded text from every page of a text-based PDF."""
    try:
        with fitz.open(pdf_path) as document:
            if document.page_count == 0:
                raise ValueError("The PDF does not contain any pages.")

            page_text = []
            for page in document:
                page_text.append(page.get_text())

            return "\n".join(page_text)
    except ValueError:
        raise
    except fitz.FileDataError as error:
        raise ValueError("The uploaded file is not a valid PDF.") from error
    except Exception as error:
        raise RuntimeError(f"PDF extraction failed: {error}") from error
