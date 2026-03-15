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

MLflow tracing:
    load_proof_folder and load_file are decorated with @mlflow.trace so they
    appear as custom spans nested inside each document's MLflow run.
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional

import fitz  # PyMuPDF
import mlflow
import pytesseract
from langchain_text_splitters import RecursiveCharacterTextSplitter
from PIL import Image

from config import MIN_TEXT_LENGTH, OCR_LANGUAGES

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown"}

# ─── Chunking Configuration ───────────────────────────────────────────────────
# Estimate: ~500 tokens is roughly 2000 characters. 100 tokens overlap is ~400 characters.
CHUNK_SIZE_CHARS = 2000
CHUNK_OVERLAP_CHARS = 400

# LangChain Text Splitter (Singleton)
_text_splitter = None

def _get_text_splitter() -> RecursiveCharacterTextSplitter:
    global _text_splitter
    if _text_splitter is None:
        _text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE_CHARS,
            chunk_overlap=CHUNK_OVERLAP_CHARS,
            separators=["\n\n", "\n", ".", " ", ""],
        )
    return _text_splitter


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


def _process_text_into_chunks(text: str, page_num: int) -> List[Dict]:
    """
    If the text exceeds the chunk limit (~2000 chars), split it into overlapping chunks.
    Otherwise, maintain it as a single intact page chunk.
    """
    chunks = []
    if len(text) <= CHUNK_SIZE_CHARS:
        chunks.append({"page_num": page_num, "text": text})
    else:
        splitter = _get_text_splitter()
        split_texts = splitter.split_text(text)
        # For chunked pages, we keep the original page number.
        # The retrieval pipeline will treat them as independent candidates.
        for i, chunk_text in enumerate(split_texts):
            chunks.append({"page_num": page_num, "text": chunk_text})
    return chunks


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
                chunks = _process_text_into_chunks(text, page_num)
                pages.extend(chunks)
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
    import re
    parts = re.split(r"\n---\s*End of Page \d+\s*---\n*", raw)

    pages = []
    for i, part in enumerate(parts):
        text = part.strip()
        if text:
            page_num = i + 1
            chunks = _process_text_into_chunks(text, page_num)
            pages.extend(chunks)

    if not pages:
        logger.warning(f"No text extracted from {Path(file_path).name}")

    return pages


# ─── Public API ───────────────────────────────────────────────────────────────

@mlflow.trace(name="load_file", span_type="LOADER")
def load_file(file_path: str) -> Optional[Dict]:
    """
    Load a single PDF or Markdown file and return a document dict.
    Returns None if the file type is unsupported or extraction yields no text.

    MLflow span attributes:
        file_path, file_name, page_count, total_chars
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

    # Log attributes visible in the MLflow span
    mlflow.get_current_active_span().set_attributes({
        "file_name":   path.name,
        "file_ext":    ext,
        "page_count":  len(pages),
        "total_chars": len(full_text),
    })

    return {
        "file_path": file_path,
        "file_name": path.name,
        "pages":     pages,
        "full_text": full_text,
    }


@mlflow.trace(name="load_proof_folder", span_type="LOADER")
def load_proof_folder(folder_path: str) -> List[Dict]:
    """
    Recursively scan a folder for PDF and Markdown files, extract their text,
    and return a list of document dicts ready for BM25 indexing.

    MLflow span attributes:
        folder_path, files_found, files_loaded, total_pages
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

    total_pages = sum(len(d["pages"]) for d in corpus)
    mlflow.get_current_active_span().set_attributes({
        "folder_path":   folder_path,
        "files_found":   len(file_paths),
        "files_loaded":  len(corpus),
        "total_pages":   total_pages,
    })

    logger.info(f"Corpus ready: {len(corpus)} document(s) loaded")
    return corpus
