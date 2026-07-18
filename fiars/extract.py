"""
extract.py — Extract searchable text from uploaded files.

Native (stdlib):  .txt, .log, .csv, .json, .eml, .html
Optional (pip):   .pdf (PyMuPDF), images (Tesseract OCR)

Missing deps don't crash — they return a clear message about what to install.
"""
from __future__ import annotations
import email
import json
import os


def extract_text(file_path: str) -> tuple[str, str]:
    """
    Extract text from a file. Returns (text, status).
    status is 'ok', 'partial', or 'unsupported'.
    """
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext in (".txt", ".log", ".csv", ".tsv", ".md", ".ini", ".cfg"):
            return _read_text(file_path), "ok"
        if ext == ".json":
            return _read_json(file_path), "ok"
        if ext == ".eml":
            return _read_eml(file_path), "ok"
        if ext in (".html", ".htm"):
            return _read_html(file_path), "ok"
        if ext == ".pdf":
            return _read_pdf(file_path)
        if ext in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
            return _read_ocr(file_path)
        return "", "unsupported"
    except Exception as e:
        return f"[Extraction error: {e}]", "partial"


def _read_text(path: str) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1", "gbk", "gb2312"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _read_json(path: str) -> str:
    data = json.loads(_read_text(path))
    return json.dumps(data, indent=2, ensure_ascii=False)


def _read_eml(path: str) -> str:
    with open(path, "rb") as f:
        msg = email.message_from_binary_file(f)
    parts = [f"From: {msg.get('from','')}", f"To: {msg.get('to','')}",
             f"Subject: {msg.get('subject','')}", f"Date: {msg.get('date','')}", ""]
    for part in msg.walk():
        ct = part.get_content_type()
        if ct == "text/plain":
            payload = part.get_payload(decode=True)
            if payload:
                parts.append(payload.decode("utf-8", errors="replace"))
    return "\n".join(parts)


def _read_html(path: str) -> str:
    import re
    text = _read_text(path)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.S | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _read_pdf(path: str) -> tuple[str, str]:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return ("[PDF support requires PyMuPDF. Install: pip install pymupdf]", "unsupported")
    doc = fitz.open(path)
    pages = [page.get_text() for page in doc]
    doc.close()
    text = "\n\n".join(pages).strip()
    return (text if text else "[PDF has no extractable text — may need OCR]", "ok" if text else "partial")


def _read_ocr(path: str) -> tuple[str, str]:
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ("[OCR requires: pip install pytesseract Pillow\n"
                "Plus Tesseract installed: https://github.com/tesseract-ocr/tesseract]",
                "unsupported")
    img = Image.open(path)
    text = pytesseract.image_to_string(img).strip()
    return (text if text else "[OCR produced no text]", "ok" if text else "partial")


