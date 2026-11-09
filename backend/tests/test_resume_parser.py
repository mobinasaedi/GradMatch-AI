import io

import docx
import pymupdf
import pytest

from app.services.resume_parser import ResumeParseError, extract_text

LONG = "Research Interests\nNatural Language Processing and machine learning in Python projects.\n" * 2


def make_pdf(text: str) -> bytes:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def make_docx(text: str) -> bytes:
    d = docx.Document()
    for line in text.splitlines():
        d.add_paragraph(line)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def test_reads_pdf():
    assert "Natural Language Processing" in extract_text("cv.pdf", make_pdf(LONG), 5_000_000)


def test_reads_docx():
    assert "machine learning" in extract_text("cv.docx", make_docx(LONG), 5_000_000)


def test_rejects_unsupported_extension():
    with pytest.raises(ResumeParseError):
        extract_text("cv.txt", b"hello" * 50, 5_000_000)


def test_rejects_empty_and_too_large():
    with pytest.raises(ResumeParseError):
        extract_text("cv.pdf", b"", 5_000_000)
    with pytest.raises(ResumeParseError):
        extract_text("cv.pdf", make_pdf(LONG), 10)


def test_rejects_corrupt_files():
    with pytest.raises(ResumeParseError):
        extract_text("cv.pdf", b"not a pdf at all" * 20, 5_000_000)
    with pytest.raises(ResumeParseError):
        extract_text("cv.docx", b"not a docx" * 20, 5_000_000)
