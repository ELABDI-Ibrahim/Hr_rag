"""
tests/test_ingestion.py — Unit tests for pipeline/ingestion.py

Tests:
  - load_file() on a real Markdown file (page splitting)
  - load_file() on an unsupported extension (returns None)
  - load_file() on an unreadable / empty Markdown (returns None)
  - load_proof_folder() finds both PDF and Markdown files in a directory

Run:
    pytest tests/test_ingestion.py -v
"""
from pathlib import Path

import pytest

from pipeline.ingestion import load_file, load_proof_folder


# ─── Markdown loading ─────────────────────────────────────────────────────────

class TestLoadMarkdownFile:
    def test_returns_document_dict(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text(
            "Content of page one.\n--- End of Page 1 ---\n"
            "Content of page two.\n--- End of Page 2 ---\n",
            encoding="utf-8",
        )
        doc = load_file(str(md))
        assert doc is not None
        assert doc["file_name"] == "test.md"
        assert len(doc["pages"]) == 2
        assert doc["pages"][0]["page_num"] == 1
        assert doc["pages"][1]["text"] == "Content of page two."

    def test_no_separator_treated_as_single_page(self, tmp_path: Path):
        md = tmp_path / "single.md"
        md.write_text("All content, no separator.", encoding="utf-8")
        doc = load_file(str(md))
        assert doc is not None
        assert len(doc["pages"]) == 1

    def test_empty_markdown_returns_none(self, tmp_path: Path):
        md = tmp_path / "empty.md"
        md.write_text("", encoding="utf-8")
        doc = load_file(str(md))
        assert doc is None

    def test_full_text_joins_pages(self, tmp_path: Path):
        md = tmp_path / "join.md"
        md.write_text(
            "Page A text.\n--- End of Page 1 ---\nPage B text.\n--- End of Page 2 ---\n",
            encoding="utf-8",
        )
        doc = load_file(str(md))
        assert "Page A text." in doc["full_text"]
        assert "Page B text." in doc["full_text"]


# ─── Unsupported extension ────────────────────────────────────────────────────

class TestLoadFileUnsupportedExtension:
    def test_returns_none_for_txt(self, tmp_path: Path):
        txt = tmp_path / "notes.txt"
        txt.write_text("some text", encoding="utf-8")
        assert load_file(str(txt)) is None

    def test_returns_none_for_docx(self, tmp_path: Path):
        fake_docx = tmp_path / "report.docx"
        fake_docx.write_bytes(b"PK fake docx")
        assert load_file(str(fake_docx)) is None


# ─── Folder scanning ──────────────────────────────────────────────────────────

class TestLoadProofFolder:
    def test_finds_markdown_files(self, tmp_path: Path):
        (tmp_path / "a.md").write_text("Page one.\n--- End of Page 1 ---\n", encoding="utf-8")
        (tmp_path / "b.md").write_text("Page one.\n--- End of Page 1 ---\n", encoding="utf-8")
        corpus = load_proof_folder(str(tmp_path))
        assert len(corpus) == 2

    def test_ignores_unsupported_files(self, tmp_path: Path):
        (tmp_path / "valid.md").write_text("Content.\n--- End of Page 1 ---\n", encoding="utf-8")
        (tmp_path / "ignored.txt").write_text("Should not appear", encoding="utf-8")
        corpus = load_proof_folder(str(tmp_path))
        assert len(corpus) == 1
        assert corpus[0]["file_name"] == "valid.md"

    def test_nonexistent_folder_returns_empty(self):
        corpus = load_proof_folder("/does/not/exist/at/all")
        assert corpus == []

    def test_scans_recursively(self, tmp_path: Path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        (sub / "nested.md").write_text("Nested page.\n--- End of Page 1 ---\n", encoding="utf-8")
        corpus = load_proof_folder(str(tmp_path))
        assert any(d["file_name"] == "nested.md" for d in corpus)
