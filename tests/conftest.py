"""
tests/conftest.py — Shared pytest fixtures for the compliance_rag test suite.

These fixtures create lightweight, temporary stand-ins for real files so that
no GPU, Tesseract, Groq API key, or live ChromaDB instance is required during
testing.
"""
import io
import pytest
from pathlib import Path


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_minimal_pdf_bytes() -> bytes:
    """
    Return a minimal, valid single-page PDF that contains the ASCII text
    'Hello World'.  Built with raw bytes so no external library is needed.
    This is intentionally tiny — just enough for fitz (PyMuPDF) to open it.
    """
    # Minimal hand-crafted PDF (text stream with "Hello World" on page 1)
    raw = (
        b"%PDF-1.4\n"
        b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
        b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n"
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
        b" /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n"
        b"4 0 obj<< /Length 44 >>\nstream\n"
        b"BT /F1 12 Tf 100 700 Td (Hello World) Tj ET\n"
        b"endstream\nendobj\n"
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000266 00000 n \n"
        b"0000000360 00000 n \n"
        b"trailer<< /Size 6 /Root 1 0 R >>\nstartxref\n441\n%%EOF"
    )
    return raw


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def tmp_proof_folder(tmp_path: Path) -> Path:
    """
    A temporary directory pre-populated with one Markdown file and one
    minimal PDF file.  Returned path can be used wherever PROOF_FOLDER is
    expected.
    """
    md_file = tmp_path / "sample.md"
    md_file.write_text(
        "This is page one content.\n--- End of Page 1 ---\n"
        "This is page two content.\n--- End of Page 2 ---\n",
        encoding="utf-8",
    )

    pdf_file = tmp_path / "sample.pdf"
    pdf_file.write_bytes(_make_minimal_pdf_bytes())

    return tmp_path


@pytest.fixture()
def sample_file_corpus(tmp_proof_folder: Path) -> list:
    """
    A tiny in-memory corpus (list of document dicts) matching the format
    produced by pipeline.ingestion.load_proof_folder.
    """
    return [
        {
            "file_path": str(tmp_proof_folder / "sample.md"),
            "file_name": "sample.md",
            "pages": [
                {"page_num": 1, "text": "This is page one content."},
                {"page_num": 2, "text": "This is page two content."},
            ],
            "full_text": "This is page one content.\n\nThis is page two content.",
        },
        {
            "file_path": str(tmp_proof_folder / "doc2.md"),
            "file_name": "doc2.md",
            "pages": [
                {"page_num": 1, "text": "Completely different document about payslips."},
            ],
            "full_text": "Completely different document about payslips.",
        },
    ]
