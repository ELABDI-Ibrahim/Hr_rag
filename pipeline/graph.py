"""
pipeline/graph.py — LangGraph HR document verification pipeline.

Graph flow for ONE required document:

    START
      │
      ▼
<<<<<<< HEAD
  keyword_suggestion   Node 1: LLM generates French keywords for the document type
      │
      ▼
  bm25_triage          Node 2: BM25 page-level scoring (query = name + keywords) → top-K pages
      │
      ▼
  semantic_search      Node 3: embed shortlisted pages → restricted similarity search → top-M pages
      │
      ▼
  verdict              Node 4: LLM checks whether retrieved pages contain the document
                               (receives keywords as additional context)
=======
  bm25_triage          Stage 1: BM25 lexical search → shortlist top-K files
      │
      ▼
  semantic_search      Stage 2: embed shortlisted pages → retrieve top-M by similarity
      │
      ▼
  verdict              Stage 3: LLM checks whether retrieved pages contain the document
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897
      │
      ▼
    END

The graph is compiled once and reused for every row in the Excel checklist.
The file corpus is passed in the initial state so it is never reloaded between runs.
"""
import logging
from typing import Any, Dict, List

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from config import BM25_TOP_K, SEMANTIC_TOP_M
<<<<<<< HEAD
from pipeline.retrieval import bm25_page_triage, semantic_page_search
from pipeline.verdict import generate_french_keywords, run_verdict
=======
from pipeline.retrieval import bm25_file_triage, semantic_page_search
from pipeline.verdict import run_verdict
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897

logger = logging.getLogger(__name__)


# ─── State Schema ─────────────────────────────────────────────────────────────

class PipelineState(TypedDict):
    """
    Shared state passed between LangGraph nodes.
    Fields are populated progressively as the graph executes.
    """
    # ── Inputs (set before invoking the graph) ────────────────────────────────
<<<<<<< HEAD
    doc_fr:      str         # Document name in French  (query + LLM context)
    doc_en:      str         # Document name in English (LLM context)
    file_corpus: List[Dict]  # All loaded documents from the candidate's proof folder

    # ── Node 1 output ─────────────────────────────────────────────────────────
    french_keywords: List[str]   # French keywords generated for this document type

    # ── Node 2 output ─────────────────────────────────────────────────────────
    candidate_pages: List[Dict]  # Pages shortlisted by BM25 (page-level)

    # ── Node 3 output ─────────────────────────────────────────────────────────
    retrieved_pages: List[Dict]  # Pages retrieved by restricted semantic search

    # ── Node 4 output ─────────────────────────────────────────────────────────
    verdict: Dict                # Final document presence verdict from the LLM
=======
    doc_fr:      str         # Document name in French  (BM25 + embedding query)
    doc_en:      str         # Document name in English (passed to LLM for context)
    file_corpus: List[Dict]  # All loaded documents from the candidate's proof folder

    # ── Stage 1 output ────────────────────────────────────────────────────────
    candidate_files: List[Dict]   # Files shortlisted by BM25

    # ── Stage 2 output ────────────────────────────────────────────────────────
    retrieved_pages: List[Dict]   # Pages retrieved by semantic search

    # ── Stage 3 output ────────────────────────────────────────────────────────
    verdict: Dict                 # Final document presence verdict from the LLM
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897


# ─── Node Functions ───────────────────────────────────────────────────────────

<<<<<<< HEAD
def keyword_suggestion_node(state: PipelineState) -> Dict[str, Any]:
    """
    Node 1 — French Keyword Suggestion.

    Calls the LLM to generate a list of French keywords typical of the
    document type being searched. These keywords are passed downstream to:
      - Node 2 (BM25): enriches the lexical query for better page recall.
      - Node 4 (Verdict): informs the LLM what to look for in the text.

    Future enhancement: replace or augment with TF-IDF / data-mining on a
    reference corpus of known document examples.
    """
    logger.info(f"[Node 1 / Keywords] Generating French keywords for: '{state['doc_fr']}'")

    keywords = generate_french_keywords(
        doc_fr=state["doc_fr"],
        doc_en=state["doc_en"],
    )

    logger.info(f"[Node 1 / Keywords] Generated {len(keywords)} keyword(s)")
    return {"french_keywords": keywords}


def bm25_triage_node(state: PipelineState) -> Dict[str, Any]:
    """
    Node 2 — BM25 Page Triage.

    Scores every individual page in the corpus using BM25. The query is
    enriched with the French keywords from Node 1 for better lexical recall.
    Returns the top-K most relevant pages (not files).
    """
    query = f"{state['doc_fr']} {state['doc_en']}"
    keywords = state.get("french_keywords", [])

    logger.info(
        f"[Node 2 / BM25] Query: '{query[:60]}' + {len(keywords)} keyword(s)"
    )

    candidates = bm25_page_triage(
        exigence=query,
        file_corpus=state["file_corpus"],
        french_keywords=keywords,
=======
def bm25_triage_node(state: PipelineState) -> Dict[str, Any]:
    """
    Node 1 — BM25 File Triage.
    Scores all files in the corpus against the document name using BM25
    and returns the top-K most likely relevant files.
    """
    # Combine FR + EN for a richer BM25 query
    query = f"{state['doc_fr']} {state['doc_en']}"
    logger.info(f"[Node 1 / BM25] Query: '{query[:70]}'")

    candidates = bm25_file_triage(
        exigence=query,
        file_corpus=state["file_corpus"],
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897
        top_k=BM25_TOP_K,
    )

    if not candidates:
<<<<<<< HEAD
        logger.warning("[Node 2 / BM25] No candidate pages found")

    return {"candidate_pages": candidates}
=======
        logger.warning("[Node 1 / BM25] No candidate files found")

    return {"candidate_files": candidates}
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897


def semantic_search_node(state: PipelineState) -> Dict[str, Any]:
    """
<<<<<<< HEAD
    Node 3 — Semantic Page Search.

    Embeds only the BM25-shortlisted pages (dedup applies — already-indexed
    pages are reused from disk). Similarity search is restricted to those
    candidate pages only (controlled by RESTRICT_SEARCH_TO_CANDIDATE_PAGES).
    """
    n = len(state.get("candidate_pages", []))
    logger.info(f"[Node 3 / Semantic] Searching {n} BM25-shortlisted page(s)")

    pages = semantic_page_search(
        exigence=state["doc_fr"],
        candidate_pages=state.get("candidate_pages", []),
=======
    Node 2 — Semantic Page Search.
    Embeds pages from BM25-shortlisted files into an ephemeral ChromaDB
    collection and retrieves the top-M most semantically relevant pages.
    """
    logger.info(f"[Node 2 / Semantic] Searching {len(state['candidate_files'])} candidate file(s)")

    # Use the French name as the primary embedding query
    pages = semantic_page_search(
        exigence=state["doc_fr"],
        candidate_files=state["candidate_files"],
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897
        top_m=SEMANTIC_TOP_M,
    )

    return {"retrieved_pages": pages}


def verdict_node(state: PipelineState) -> Dict[str, Any]:
    """
<<<<<<< HEAD
    Node 4 — LLM Verdict.

    Asks Groq whether the retrieved pages contain the required document.
    Also receives the French keywords as extra context to guide the LLM.
    Returns a structured verdict dict.
    """
    logger.info(
        f"[Node 4 / LLM] Checking '{state['doc_fr']}' "
        f"({len(state['retrieved_pages'])} page(s))"
    )
=======
    Node 3 — LLM Verdict.
    Asks Groq whether the retrieved pages contain the required document.
    Returns a structured verdict dict.
    """
    logger.info(f"[Node 3 / LLM] Checking '{state['doc_fr']}' ({len(state['retrieved_pages'])} page(s))")
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897

    verdict = run_verdict(
        doc_fr=state["doc_fr"],
        doc_en=state["doc_en"],
        retrieved_pages=state["retrieved_pages"],
<<<<<<< HEAD
        french_keywords=state.get("french_keywords", []),
=======
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897
    )

    status_icon = "✅" if verdict.get("satisfied") else "❌"
    logger.info(
<<<<<<< HEAD
        f"[Node 4 / LLM] {status_icon} {verdict.get('confidence', '').upper()} — "
=======
        f"[Node 3 / LLM] {status_icon} {verdict.get('confidence', '').upper()} — "
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897
        f"{verdict.get('justification', '')[:80]}"
    )

    return {"verdict": verdict}


# ─── Graph Builder ────────────────────────────────────────────────────────────

def build_compliance_graph():
    """
<<<<<<< HEAD
    Assemble and compile the 4-node LangGraph HR document verification pipeline.
=======
    Assemble and compile the 3-node LangGraph HR document verification pipeline.
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897

    Returns:
        A compiled LangGraph runnable — call .invoke(initial_state) to run.
    """
    graph = StateGraph(PipelineState)

<<<<<<< HEAD
    graph.add_node("keyword_suggestion", keyword_suggestion_node)
    graph.add_node("bm25_triage",        bm25_triage_node)
    graph.add_node("semantic_search",    semantic_search_node)
    graph.add_node("verdict",            verdict_node)

    graph.set_entry_point("keyword_suggestion")
    graph.add_edge("keyword_suggestion", "bm25_triage")
    graph.add_edge("bm25_triage",        "semantic_search")
    graph.add_edge("semantic_search",    "verdict")
    graph.add_edge("verdict",            END)
=======
    graph.add_node("bm25_triage",     bm25_triage_node)
    graph.add_node("semantic_search", semantic_search_node)
    graph.add_node("verdict",         verdict_node)

    graph.set_entry_point("bm25_triage")
    graph.add_edge("bm25_triage",     "semantic_search")
    graph.add_edge("semantic_search", "verdict")
    graph.add_edge("verdict",         END)
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897

    return graph.compile()
