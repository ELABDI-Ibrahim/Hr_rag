"""
tests/test_verdict.py — Unit tests for pipeline/verdict.py

Tests:
  - _format_context: empty pages → warning string; populated → excerpt blocks
  - generate_french_keywords: happy path (mocked LLM) + error fallback
  - run_verdict: happy path with mocked LLM; keywords injected; error fallback

Run:
    pytest tests/test_verdict.py -v
"""
from unittest.mock import MagicMock, patch

import pytest

from pipeline.verdict import _format_context, DocumentVerdict


# ─── _format_context ─────────────────────────────────────────────────────────

class TestFormatContext:
    def test_empty_pages_returns_warning_string(self):
        result = _format_context([])
        assert "Aucun" in result or "pertinent" in result

    def test_single_page_contains_filename_and_page_num(self):
        pages = [{"text": "Sample content", "source_file": "cv.pdf", "page_num": 3}]
        result = _format_context(pages)
        assert "cv.pdf" in result
        assert "3" in result
        assert "Sample content" in result

    def test_text_truncated_at_max_chars(self):
        long_text = "A" * 2000
        pages = [{"text": long_text, "source_file": "x.pdf", "page_num": 1}]
        result = _format_context(pages)
        assert "tronqué" in result or "truncated" in result

    def test_multiple_pages_both_present(self):
        pages = [
            {"text": "Page one text", "source_file": "a.pdf", "page_num": 1},
            {"text": "Page two text", "source_file": "a.pdf", "page_num": 2},
        ]
        result = _format_context(pages)
        assert "Page one text" in result
        assert "Page two text" in result


# ─── generate_french_keywords ─────────────────────────────────────────────────

class TestGenerateFrenchKeywords:
    @patch("pipeline.verdict._build_llm")
    def test_happy_path_returns_list(self, mock_build_llm):
        from pipeline.verdict import generate_french_keywords

        mock_llm = MagicMock()
        mock_llm_instance = MagicMock()
        mock_resp = MagicMock()
        mock_resp.content = "curriculum vitae, expériences professionnelles, diplôme, compétences"
        mock_llm_instance.invoke.return_value = mock_resp
        # Simulate prompt | llm chain
        mock_build_llm.return_value = mock_llm_instance

        with patch("pipeline.verdict._KEYWORD_PROMPT.__or__", return_value=mock_llm_instance):
            result = generate_french_keywords("Curriculum Vitae", "Resume / CV")

        # Result should be a list of strings
        assert isinstance(result, list)

    @patch("pipeline.verdict._build_llm")
    def test_llm_error_returns_empty_list(self, mock_build_llm):
        from pipeline.verdict import generate_french_keywords

        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.side_effect = RuntimeError("timeout")
        mock_build_llm.return_value = mock_llm_instance

        with patch("pipeline.verdict._KEYWORD_PROMPT.__or__", return_value=mock_llm_instance):
            result = generate_french_keywords("Attestation", "Certificate")

        assert result == []


# ─── run_verdict ──────────────────────────────────────────────────────────────

class TestRunVerdict:
    def _make_fake_verdict(self) -> DocumentVerdict:
        return DocumentVerdict(
            satisfied=True,
            confidence="high",
            justification="Le CV est clairement présent.",
            source_file="cv.pdf",
            source_page=1,
        )

    @patch("pipeline.verdict._build_llm")
    def test_happy_path_returns_dict(self, mock_build_llm):
        from pipeline.verdict import run_verdict

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = self._make_fake_verdict()
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_chain
        mock_build_llm.return_value = mock_llm

        with patch("pipeline.verdict.VERDICT_PROMPT.__or__", return_value=mock_chain):
            result = run_verdict(
                doc_fr="Curriculum Vitae",
                doc_en="Resume / CV",
                retrieved_pages=[{"text": "John Doe CV", "source_file": "cv.pdf", "page_num": 1}],
                french_keywords=["curriculum vitae", "diplôme"],
            )

        assert result["satisfied"] is True
        assert result["confidence"] == "high"
        assert result["source_file"] == "cv.pdf"

    @patch("pipeline.verdict._build_llm")
    def test_keywords_passed_to_prompt(self, mock_build_llm):
        """Verify that french_keywords end up in the invoke call args."""
        from pipeline.verdict import run_verdict

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = self._make_fake_verdict()
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_chain
        mock_build_llm.return_value = mock_llm

        keywords = ["carte d'identité", "nom", "date de naissance"]

        with patch("pipeline.verdict.VERDICT_PROMPT.__or__", return_value=mock_chain):
            run_verdict("Pièce d'identité", "ID Card", [], french_keywords=keywords)

        call_kwargs = mock_chain.invoke.call_args[0][0]
        assert "keywords_section" in call_kwargs
        for kw in keywords:
            assert kw in call_kwargs["keywords_section"]

    @patch("pipeline.verdict._build_llm")
    def test_llm_error_returns_safe_fallback(self, mock_build_llm):
        from pipeline.verdict import run_verdict

        mock_chain = MagicMock()
        mock_chain.invoke.side_effect = RuntimeError("API timeout")
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_chain
        mock_build_llm.return_value = mock_llm

        with patch("pipeline.verdict.VERDICT_PROMPT.__or__", return_value=mock_chain):
            result = run_verdict("CV", "Resume", [], french_keywords=[])

        assert result["satisfied"] is False
        assert result["confidence"] == "low"
        assert result["source_file"] == "N/A"
        assert result["source_page"] == 0

    @patch("pipeline.verdict._build_llm")
    def test_no_keywords_still_runs(self, mock_build_llm):
        from pipeline.verdict import run_verdict

        mock_chain = MagicMock()
        mock_chain.invoke.return_value = DocumentVerdict(
            satisfied=False, confidence="low",
            justification="Aucun extrait.", source_file="N/A", source_page=0,
        )
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value = mock_chain
        mock_build_llm.return_value = mock_llm

        with patch("pipeline.verdict.VERDICT_PROMPT.__or__", return_value=mock_chain):
            result = run_verdict("Attestation de travail", "Work Certificate", [])

        assert result["satisfied"] is False
