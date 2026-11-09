"""Extract plain text from uploaded PDF / DOCX resumes (fully local, no paid services)."""

import io
import os


class ResumeParseError(ValueError):
    pass


ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def extract_text(filename: str, data: bytes, max_bytes: int) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ResumeParseError("Only PDF and DOCX resumes are supported.")
    if not data:
        raise ResumeParseError("The uploaded file is empty.")
    if len(data) > max_bytes:
        raise ResumeParseError(f"File is too large (limit {max_bytes // (1024 * 1024)} MB).")

    text = _read_pdf(data) if ext == ".pdf" else _read_docx(data)
    text = text.replace("\x00", "").strip()
    if len(text) < 50:
        raise ResumeParseError(
            "Could not read enough text from the file. Scanned/image-only PDFs are not "
            "supported yet (no OCR in the MVP)."
        )
    return text


def _read_pdf(data: bytes) -> str:
    import pymupdf  # PyMuPDF

    try:
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc)
    except Exception as exc:  # corrupted / encrypted files
        raise ResumeParseError("The PDF could not be read.") from exc


def _read_docx(data: bytes) -> str:
    import docx

    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:
        raise ResumeParseError("The DOCX file could not be read.") from exc

    parts = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n".join(parts)
