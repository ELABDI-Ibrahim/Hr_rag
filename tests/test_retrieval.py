"""
tests/test_retrieval.py — Unit tests for pipeline/retrieval.py

Tests:
  - _page_id: deterministic content-hash behaviour
  - _build_metadata: all expected fields present and correct
  - bm25_page_triage: page-level scoring, keyword enrichment, zero-score exclusion
  - _index_new_pages dedup: cold / warm / partial runs (mocked ChromaDB)
  - semantic_page_search restricted mode: uses ChromaDB WHERE filter (not a Python loop)
  - semantic_page_search unrestricted mode: calls similarity_search without filter

Run:
    pytest tests/test_retrieval.py -v
"""
import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from pipeline.retrieval import _page_id, _build_metadata, bm25_page_triage


# ─── _page_id helper ─────────────────────────────────────────────────────────

class TestPageId:
    def test_same_text_same_id(self):
        assert _page_id("hello world") == _page_id("hello world")

    def test_different_text_different_id(self):
        assert _page_id("text A") != _page_id("text B")

    def test_is_sha256_hex(self):
        assert _page_id("test") == hashlib.sha256("test".encode()).hexdigest()

    def test_empty_string_stable(self):
        result = _page_id("")
        assert isinstance(result, str) and len(result) == 64


# ─── _build_metadata ─────────────────────────────────────────────────────────

class TestBuildMetadata:
    def _make_page(self, text="Hello", source="doc.pdf",
                   path="/proof/doc.pdf", page_num=2):
        return {"text": text, "source_file": source,
                "file_path": path, "page_num": page_num}

    def test_contains_all_required_fields(self):
        meta = _build_metadata(self._make_page())
        for field in ("content_id", "source_file", "file_path", "page_num", "file_ext"):
            assert field in meta, f"Missing metadata field: {field}"

    def test_content_id_matches_page_id(self):
        page = self._make_page(text="Some text here")
        meta = _build_metadata(page)
        assert meta["content_id"] == _page_id("Some text here")

    def test_file_ext_extracted_correctly(self):
        meta_pdf = _build_metadata(self._make_page(path="/proof/report.pdf"))
        meta_md  = _build_metadata(self._make_page(path="/proof/notes.md"))
        assert meta_pdf["file_ext"] == ".pdf"
        assert meta_md["file_ext"] == ".md"

    def test_source_file_and_page_num_preserved(self):
        meta = _build_metadata(self._make_page(source="cv.pdf", page_num=5))
        assert meta["source_file"] == "cv.pdf"
        assert meta["page_num"] == 5

    def test_missing_file_path_gives_empty_ext(self):
        page = {"text": "x", "source_file": "f.pdf", "page_num": 1}
        meta = _build_metadata(page)
        assert meta["file_ext"] == ""


# ─── BM25 page triage ─────────────────────────────────────────────────────────

class TestBM25PageTriage:
    def test_empty_corpus_returns_empty(self):
        assert bm25_page_triage("any query", []) == []

    def test_results_are_page_dicts(self, sample_file_corpus):
        results = bm25_page_triage("page content", sample_file_corpus)
        if results:
            assert "text" in results[0]
            assert "source_file" in results[0]
            assert "page_num" in results[0]
            assert "pages" not in results[0]    # must not be file-level
            assert "full_text" not in results[0]

    def test_keyword_boost(self, sample_file_corpus):
        results = bm25_page_triage(
            "document", sample_file_corpus, french_keywords=["payslips"]
        )
        assert isinstance(results, list)

    def test_top_k_limit_respected(self, sample_file_corpus):
        results = bm25_page_triage("page content", sample_file_corpus, top_k=1)
        assert len(results) <= 1

    def test_zero_score_excluded(self, sample_file_corpus):
        assert bm25_page_triage("xyzqqqnomatch", sample_file_corpus) == []

    def test_pages_from_multiple_files_scored(self, sample_file_corpus):
        results = bm25_page_triage("page content payslips", sample_file_corpus, top_k=10)
        assert len(results) <= 3   # 2 pages in sample.md + 1 in doc2.md


# ─── Dedup / indexing logic ───────────────────────────────────────────────────

class TestDedupLogic:
    def _make_mock_client(self, existing_ids):
        col = MagicMock()
        col.get.return_value = {"ids": existing_ids}
        client = MagicMock()
        client.get_or_create_collection.return_value = col
        return client

    def _two_pages(self):
        return [
            {"text": "Page one content.", "source_file": "s.md",
             "file_path": "/s.md", "page_num": 1},
            {"text": "Page two content.", "source_file": "s.md",
             "file_path": "/s.md", "page_num": 2},
        ]

    @patch("pipeline.retrieval.Chroma.from_documents")
    @patch("pipeline.retrieval._get_chroma_client")
    def test_cold_run_embeds_all(self, mock_client, mock_from_docs):
        from pipeline.retrieval import _index_new_pages
        mock_client.return_value = self._make_mock_client([])
        _index_new_pages(self._two_pages(), MagicMock())
        mock_from_docs.assert_called_once()
        _, kw = mock_from_docs.call_args
        assert len(kw["documents"]) == 2

    @patch("pipeline.retrieval.Chroma.from_documents")
    @patch("pipeline.retrieval._get_chroma_client")
    def test_warm_run_embeds_nothing(self, mock_client, mock_from_docs):
        from pipeline.retrieval import _index_new_pages
        pages = self._two_pages()
        all_ids = [_page_id(p["text"]) for p in pages]
        mock_client.return_value = self._make_mock_client(all_ids)
        _index_new_pages(pages, MagicMock())
        mock_from_docs.assert_not_called()

    @patch("pipeline.retrieval.Chroma.from_documents")
    @patch("pipeline.retrieval._get_chroma_client")
    def test_partial_run_embeds_new_only(self, mock_client, mock_from_docs):
        from pipeline.retrieval import _index_new_pages
        pages = self._two_pages()
        all_ids = [_page_id(p["text"]) for p in pages]
        mock_client.return_value = self._make_mock_client([all_ids[0]])
        _index_new_pages(pages, MagicMock())
        mock_from_docs.assert_called_once()
        _, kw = mock_from_docs.call_args
        assert len(kw["documents"]) == 1
        assert kw["documents"][0].page_content == pages[1]["text"]

    @patch("pipeline.retrieval.Chroma.from_documents")
    @patch("pipeline.retrieval._get_chroma_client")
    def test_content_id_stored_in_metadata(self, mock_client, mock_from_docs):
        """Each indexed Document must carry content_id in its metadata."""
        from pipeline.retrieval import _index_new_pages
        mock_client.return_value = self._make_mock_client([])
        _index_new_pages(self._two_pages(), MagicMock())
        _, kw = mock_from_docs.call_args
        for doc in kw["documents"]:
            assert "content_id" in doc.metadata
            assert doc.metadata["content_id"] == _page_id(doc.page_content)


# ─── Restricted search uses ChromaDB WHERE filter ────────────────────────────

class TestRestrictedSearch:
    """
    Verify that restrict_to_candidates=True passes a WHERE filter to
    ChromaDB's similarity_search — NOT a Python cosine loop.
    """

    def _make_mock_client(self, existing_ids):
        col = MagicMock()
        col.get.return_value = {"ids": existing_ids}
        client = MagicMock()
        client.get_or_create_collection.return_value = col
        return client

    def _candidate_pages(self):
        return [
            {"text": "alpha beta gamma", "source_file": "f.md",
             "file_path": "/f.md", "page_num": 1},
        ]

    @patch("pipeline.retrieval.Chroma")
    @patch("pipeline.retrieval._get_chroma_client")
    @patch("pipeline.retrieval._get_embeddings")
    def test_restricted_uses_where_filter(self, mock_emb, mock_client, mock_chroma_cls):
        """
        When restrict_to_candidates=True, similarity_search must be called
        with filter={'content_id': {'$in': [...]}}
        """
        from langchain_core.documents import Document
        from pipeline.retrieval import semantic_page_search

        pages = self._candidate_pages()
        candidate_id = _page_id(pages[0]["text"])

        mock_client.return_value = self._make_mock_client(existing_ids=[candidate_id])

        fake_doc = Document(
            page_content="alpha beta gamma",
            metadata={"source_file": "f.md", "file_path": "/f.md",
                      "page_num": 1, "file_ext": ".md", "content_id": candidate_id},
        )
        mock_vs = mock_chroma_cls.return_value
        mock_vs.similarity_search.return_value = [fake_doc]

        with patch("pipeline.retrieval.Chroma.from_documents"):
            results = semantic_page_search(
                exigence="alpha",
                candidate_pages=pages,
                top_m=1,
                restrict_to_candidates=True,
            )

        # The call must include the WHERE filter
        call_args = mock_vs.similarity_search.call_args
        assert "filter" in call_args.kwargs or (
            len(call_args.args) >= 3 and call_args.args[2] is not None
        ), "similarity_search must be called with a filter argument"

        filter_arg = call_args.kwargs.get("filter") or {}
        assert "content_id" in filter_arg
        assert "$in" in filter_arg["content_id"]
        assert candidate_id in filter_arg["content_id"]["$in"]

    @patch("pipeline.retrieval.Chroma")
    @patch("pipeline.retrieval._get_chroma_client")
    @patch("pipeline.retrieval._get_embeddings")
    def test_unrestricted_no_filter(self, mock_emb, mock_client, mock_chroma_cls):
        """
        When restrict_to_candidates=False, similarity_search is called
        without any filter (global collection search).
        """
        from langchain_core.documents import Document
        from pipeline.retrieval import semantic_page_search

        pages = self._candidate_pages()
        candidate_id = _page_id(pages[0]["text"])
        mock_client.return_value = self._make_mock_client(existing_ids=[candidate_id])

        fake_doc = Document(
            page_content="alpha beta gamma",
            metadata={"source_file": "f.md", "file_path": "/f.md",
                      "page_num": 1, "file_ext": ".md", "content_id": candidate_id},
        )
        mock_vs = mock_chroma_cls.return_value
        mock_vs.similarity_search.return_value = [fake_doc]

        with patch("pipeline.retrieval.Chroma.from_documents"):
            results = semantic_page_search(
                exigence="alpha",
                candidate_pages=pages,
                top_m=1,
                restrict_to_candidates=False,
            )

        call_args = mock_vs.similarity_search.call_args
        # No filter key, or filter is None/absent
        filter_arg = call_args.kwargs.get("filter", None)
        assert filter_arg is None

    @patch("pipeline.retrieval.Chroma")
    @patch("pipeline.retrieval._get_chroma_client")
    @patch("pipeline.retrieval._get_embeddings")
    def test_retrieved_pages_have_full_metadata(self, mock_emb, mock_client, mock_chroma_cls):
        """Retrieved dicts must include source_file, file_path, page_num, file_ext."""
        from langchain_core.documents import Document
        from pipeline.retrieval import semantic_page_search

        pages = self._candidate_pages()
        candidate_id = _page_id(pages[0]["text"])
        mock_client.return_value = self._make_mock_client(existing_ids=[candidate_id])

        fake_doc = Document(
            page_content="alpha beta gamma",
            metadata={"source_file": "f.md", "file_path": "/f.md",
                      "page_num": 1, "file_ext": ".md", "content_id": candidate_id},
        )
        mock_chroma_cls.return_value.similarity_search.return_value = [fake_doc]

        with patch("pipeline.retrieval.Chroma.from_documents"):
            results = semantic_page_search("alpha", pages, top_m=1,
                                           restrict_to_candidates=False)

        assert len(results) == 1
        r = results[0]
        for field in ("text", "source_file", "file_path", "page_num", "file_ext"):
            assert field in r, f"Missing field in retrieved page: {field}"
