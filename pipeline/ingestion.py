"""
pipeline/ingestion.py — File loading and text extraction.

Supports:
  - PDF  → PyMuPDF (digital text) with Tesseract OCR fallback for scanned pages
  - Markdown (.md / .markdown) → plain text read

Each file is represented as:
    {
        "file_path": str,
        "file_name": str,
        "pages":     [{"page_num": int, "text": str}, ...],
        "full_text": str,   ← concatenation of all pages, used for BM25 indexing
    }
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from config import MIN_TEXT_LENGTH, OCR_LANGUAGES

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown"}


# ─── PDF ──────────────────────────────────────────────────────────────────────

def _page_to_image(page: fitz.Page) -> Image.Image:
    """Render a PDF page to a PIL Image for OCR (300 DPI for good accuracy)."""
    pix = page.get_pixmap(dpi=300)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


def _extract_page_text(page: fitz.Page, page_num: int, file_name: str) -> str:
    """
    Try digital text extraction first.
    If the result is too short (likely a scanned image), fall back to Tesseract OCR.
    """
    text = page.get_text().strip()

    if len(text) >= MIN_TEXT_LENGTH:
        return text

    # Scanned page detected → OCR
    logger.info(f"  [{file_name}] Page {page_num}: short text ({len(text)} chars) — using OCR")
    try:
        img = _page_to_image(page)
        text = pytesseract.image_to_string(img, lang=OCR_LANGUAGES).strip()
    except Exception as e:
        logger.warning(f"  [{file_name}] Page {page_num}: OCR failed — {e}")
        text = ""

    return text


def _load_pdf(file_path: str) -> List[Dict]:
    """Extract text from every page of a PDF. Returns list of {page_num, text}."""
    pages = []
    try:
        doc = fitz.open(file_path)
        file_name = Path(file_path).name
        for page_index, page in enumerate(doc):
            page_num = page_index + 1
            text = _extract_page_text(page, page_num, file_name)
            if text:
                pages.append({"page_num": page_num, "text": text})
        doc.close()
    except Exception as e:
        logger.error(f"Failed to open PDF {file_path}: {e}")
    return pages


# ─── Markdown ─────────────────────────────────────────────────────────────────

# Separator written at the end of each simulated page
MD_PAGE_SEPARATOR = "--- End of Page"


def _load_markdown(file_path: str) -> List[Dict]:
    """
    Read a Markdown file and split it into pages using the separator:
        --- End of Page {N} ---
    If no separator is found, the whole file is treated as a single page.
    """
    try:
        raw = Path(file_path).read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to read Markdown {file_path}: {e}")
        return []

    # Split on the page-end marker (keep content before each marker as one page)
    # e.g.  "content page 1\n--- End of Page 1 ---\n\ncontent page 2\n--- End of Page 2 ---"
    import re
    parts = re.split(r"\n---\s*End of Page \d+\s*---\n*", raw)

    pages = []
    for i, part in enumerate(parts):
        text = part.strip()
        if text:
            pages.append({"page_num": i + 1, "text": text})

    if not pages:
        logger.warning(f"No text extracted from {Path(file_path).name}")

    return pages


# ─── Public API ───────────────────────────────────────────────────────────────

def load_file(file_path: str) -> Optional[Dict]:
    """
    Load a single PDF or Markdown file and return a document dict.
    Returns None if the file type is unsupported or extraction yields no text.
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        pages = _load_pdf(file_path)
    elif ext in (".md", ".markdown"):
        pages = _load_markdown(file_path)
    else:
        logger.warning(f"Unsupported extension '{ext}' — skipping {path.name}")
        return None

    if not pages:
        logger.warning(f"No text extracted from {path.name} — skipping")
        return None

    full_text = "\n\n".join(p["text"] for p in pages)
    return {
        "file_path": file_path,
        "file_name": path.name,
        "pages": pages,
        "full_text": full_text,
    }


def load_proof_folder(folder_path: str) -> List[Dict]:
    """
    Recursively scan a folder for PDF and Markdown files, extract their text,
    and return a list of document dicts ready for BM25 indexing.
    """
    folder = Path(folder_path)
    if not folder.exists():
        logger.error(f"Proof folder not found: {folder_path}")
        return []

    file_paths = [f for f in folder.rglob("*") if f.suffix.lower() in SUPPORTED_EXTENSIONS]
    logger.info(f"Found {len(file_paths)} file(s) in '{folder_path}'")

    corpus = []
    for file_path in sorted(file_paths):
        logger.info(f"Loading: {file_path.name}")
        doc = load_file(str(file_path))
        if doc:
            corpus.append(doc)
            logger.info(f"  → {len(doc['pages'])} page(s), {len(doc['full_text'])} chars")

    logger.info(f"Corpus ready: {len(corpus)} document(s) loaded")
    return corpus
