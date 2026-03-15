"""
pipeline/retrieval.py — Two-stage retrieval.

Stage 1 — BM25 page triage (coarse, lexical):
    Score every individual page across the entire corpus using BM25.
    The query is enriched with LLM-generated French keywords (from Node 1)
    for better recall. Returns the top-K highest-scoring pages.

Stage 2 — Semantic page search (fine, embedding-based):
    Embed only the BM25-shortlisted pages into a persistent ChromaDB
    collection stored on disk.

    Deduplication (content-hash):
        Each page ID = sha256(page_text). Pages already indexed from a
        previous run are skipped — their embeddings are reused from disk.

    Restricted search (configurable, default True):
        When RESTRICT_SEARCH_TO_CANDIDATE_PAGES=True, ChromaDB's native
        similarity search is scoped to only the BM25 candidate pages using
        a metadata WHERE filter:  content_id IN [candidate_ids]
        This is fully inside ChromaDB's ANN engine — no Python loop needed.

    Rich page metadata:
        Every indexed page stores the following metadata fields so results
        are always traceable:
            content_id   — sha256(page_text)   used for restricted filtering
            source_file  — file name (e.g. "cv_dupont.pdf")
            file_path    — absolute or relative path to the source file
            page_num     — page number within the source file
            file_ext     — file extension (".pdf", ".md", etc.)
"""
import hashlib
import logging
from typing import Dict, List, Optional, Tuple

import chromadb
import mlflow
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from nltk.tokenize import word_tokenize
from rank_bm25 import BM25Okapi

from config import (
    BM25_TOP_K,
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    EMBEDDING_MODEL,
    RESTRICT_SEARCH_TO_CANDIDATE_PAGES,
    SEMANTIC_TOP_M,
)

logger = logging.getLogger(__name__)


# ─── Embeddings (singleton — loaded once, reused for all queries) ─────────────

_embeddings: Optional[HuggingFaceEmbeddings] = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    global _embeddings
    if _embeddings is None:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return _embeddings


# ─── Persistent ChromaDB client (singleton) ───────────────────────────────────

_chroma_client: Optional[chromadb.PersistentClient] = None


def _get_chroma_client() -> chromadb.PersistentClient:
    """Return (or lazily create) the shared persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        logger.info(f"Persistent ChromaDB at: {CHROMA_PERSIST_DIR}")
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return _chroma_client


# ─── Content-hash helper ──────────────────────────────────────────────────────

def _page_id(page_text: str) -> str:
    """
    Deterministic document ID based on page content.
    sha256(page_text) guarantees:
      - Same content → same ID → never re-embedded (dedup).
      - Changed content → new ID → automatically re-indexed.
    The same hash is also stored as metadata field 'content_id' so ChromaDB's
    WHERE filter can restrict similarity search to candidate pages.
    """
    return hashlib.sha256(page_text.encode("utf-8")).hexdigest()


def _build_metadata(page_dict: Dict) -> Dict:
    """
    Build the full metadata dict stored alongside every page embedding.

    Fields:
        content_id  — sha256(page_text) — used for restricted WHERE filtering
        source_file — file name only (e.g. "cv_dupont.pdf")
        file_path   — full path to the source file
        page_num    — page number within the source file (1-indexed)
        file_ext    — lowercase file extension (".pdf", ".md", …)
    """
    from pathlib import Path
    text = page_dict["text"]
    file_path = page_dict.get("file_path", "")
    return {
        "content_id":  _page_id(text),
        "source_file": page_dict.get("source_file", ""),
        "file_path":   file_path,
        "page_num":    page_dict.get("page_num", 0),
        "file_ext":    str(Path(file_path).suffix).lower() if file_path else "",
    }


def _tokenize_text(text: str) -> List[str]:
    """
    Robust NLTK word tokenization. Ensures the same tokenization is
    applied to both documents and the query for BM25 scoring.
    """
    # Using lowercase and word_tokenize handles punctuation and mixed languages better
    # than simple whitespace splitting.
    return [t for t in word_tokenize(text.lower()) if t.isalnum()]


# ─── Stage 1: BM25 Page Triage ───────────────────────────────────────────────

@mlflow.trace(name="bm25_page_triage", span_type="RETRIEVER")
def bm25_page_triage(
    exigence: str,
    file_corpus: List[Dict],
    french_keywords: Optional[List[str]] = None,
    top_k: int = BM25_TOP_K,
) -> List[Dict]:
    """
    Score every individual page across the entire corpus using BM25.
    The query is formed from:
        exigence + (optional) LLM-generated French keywords

    Args:
        exigence:         Query string (doc_fr + doc_en).
        file_corpus:      All loaded documents from the proof folder.
        french_keywords:  French keywords generated by the keyword_suggestion node.
        top_k:            Maximum number of pages to shortlist.

    Returns:
        List of page dicts: {text, source_file, file_path, page_num}
        sorted by BM25 score descending.
    """
    if not file_corpus:
        logger.warning("BM25 page triage: corpus is empty")
        return []

    # Flatten all pages across all files into a single list
    all_pages: List[Dict] = []
    for file_doc in file_corpus:
        for page in file_doc["pages"]:
            text = page["text"].strip()
            if not text:
                continue
            all_pages.append({
                "text":        text,
                "source_file": file_doc["file_name"],
                "file_path":   file_doc["file_path"],
                "page_num":    page["page_num"],
            })

    if not all_pages:
        logger.warning("BM25 page triage: no pages found in corpus")
        return []

    # Build query: document name + French keywords for richer lexical matching
    keyword_str  = " ".join(french_keywords) if french_keywords else ""
    full_query   = f"{exigence} {keyword_str}".strip()
    query_tokens = full_query.lower().split()

    # Tokenize each page consistently
    tokenized_pages = [_tokenize_text(p["text"]) for p in all_pages]
    bm25 = BM25Okapi(tokenized_pages)
    
    # Tokenize the query identically
    query_tokens = _tokenize_text(full_query)
    scores = bm25.get_scores(query_tokens)

    # Sort descending, keep only positive scores, respect top_k limit (Check if this needed)
    sorted_indices = scores.argsort()[::-1][:top_k]
    candidates = [all_pages[i] for i in sorted_indices if scores[i] > 0]

    logger.info(
        f"BM25 page triage: shortlisted {len(candidates)}/{len(all_pages)} page(s) "
        f"[query tokens: {len(query_tokens)}, "
        f"top scores: {[round(scores[i], 2) for i in sorted_indices[:3]]}]"
    )

    span = mlflow.get_current_active_span()
    if span:
        span.set_attributes({
            "total_pages":       len(all_pages),
            "shortlisted_pages": len(candidates),
            "query_token_count": len(query_tokens),
            "keyword_count":     len(french_keywords) if french_keywords else 0,
            "top_bm25_score":    round(float(scores[sorted_indices[0]]), 4) if len(sorted_indices) > 0 else 0.0,
        })
    return candidates


# ─── Stage 2: Semantic Page Search ───────────────────────────────────────────

@mlflow.trace(name="_index_new_pages", span_type="RETRIEVER")
def _index_new_pages(
    page_dicts: List[Dict],
    embeddings: HuggingFaceEmbeddings,
) -> List[str]:
    """
    Index any BM25-shortlisted pages not yet in the persistent ChromaDB
    collection (content-hash dedup). Each page is stored with rich metadata
    including 'content_id' so ChromaDB's WHERE filter can scope searches.

    Args:
        page_dicts: BM25-shortlisted page dicts {text, source_file, file_path, page_num}.
        embeddings: HuggingFace embedding model.

    Returns:
        all_ids — sha256 IDs for every candidate page (existing + newly added).
    """
    client = _get_chroma_client()

    # Build LangChain Document objects with full metadata
    documents = [
        Document(
            page_content=p["text"],
            metadata=_build_metadata(p),
        )
        for p in page_dicts
    ]
    all_ids = [doc.metadata["content_id"] for doc in documents]

    # Check which IDs already exist in the collection
    try:
        existing = client.get_or_create_collection(CHROMA_COLLECTION_NAME).get(
            ids=all_ids, include=[]   # include=[] → return IDs only, no vectors
        )
        existing_ids: set = set(existing["ids"])
    except Exception:
        existing_ids = set()

    new_docs = [doc for doc in documents if doc.metadata["content_id"] not in existing_ids]
    new_ids  = [doc.metadata["content_id"] for doc in new_docs]

    already_count = len(all_ids) - len(new_docs)
    logger.info(
        f"Dedup: {already_count} page(s) already indexed, "
        f"embedding {len(new_docs)} new page(s)"
    )

    if new_docs:
        Chroma.from_documents(
            documents=new_docs,
            embedding=embeddings,
            collection_name=CHROMA_COLLECTION_NAME,
            client=client,
            ids=new_ids,
        )
        logger.info(f"Indexed {len(new_docs)} new page(s) into '{CHROMA_COLLECTION_NAME}'")

    span = mlflow.get_current_active_span()
    if span:
        span.set_attributes({
            "total_candidate_pages": len(all_ids),
            "already_indexed":       already_count,
            "newly_embedded":        len(new_docs),
            "collection_name":       CHROMA_COLLECTION_NAME,
        })

    return all_ids


@mlflow.trace(name="semantic_page_search", span_type="RETRIEVER")
def semantic_page_search(
    exigence: str,
    candidate_pages: List[Dict],
    top_m: int = SEMANTIC_TOP_M,
    restrict_to_candidates: bool = RESTRICT_SEARCH_TO_CANDIDATE_PAGES,
) -> List[Dict]:
    """
    Embed and index the BM25-shortlisted pages (dedup applies), then search.

    When restrict_to_candidates=True (default), ChromaDB's native similarity
    search is scoped to the candidate pages only using a WHERE filter on the
    'content_id' metadata field:
        filter={"content_id": {"$in": candidate_ids}}
    This runs fully inside ChromaDB's vector engine — no Python loops.

    Args:
        exigence:              Search query string.
        candidate_pages:       BM25-shortlisted pages {text, source_file, file_path, page_num}.
        top_m:                 Number of pages to retrieve.
        restrict_to_candidates: Scope search to candidate pages only (default True).

    Returns:
        List of {text, source_file, file_path, page_num, file_ext} dicts.
    """
    if not candidate_pages:
        logger.warning("Semantic search: no candidate pages — skipping embedding step")
        return []

    embeddings = _get_embeddings()

    # Dedup + incremental indexing (also returns all content_id hashes)
    all_ids = _index_new_pages(candidate_pages, embeddings)

    k = min(top_m, len(candidate_pages))

    vectorstore = Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        client=_get_chroma_client(),
    )

    if restrict_to_candidates:
        # ── Native ChromaDB WHERE filter — search inside candidate pages only ──
        logger.info(
            f"Semantic search: restricted to {len(all_ids)} candidate page(s) "
            f"via ChromaDB WHERE filter"
        )
        results = vectorstore.similarity_search(
            exigence,
            k=k,
            filter={"content_id": {"$in": all_ids}},
        )
    else:
        # ── Unrestricted — search the full collection ─────────────────────────
        logger.info("Semantic search: unrestricted — searching full collection")
        results = vectorstore.similarity_search(exigence, k=k)

    retrieved = [
        {
            "text":        doc.page_content,
            "source_file": doc.metadata.get("source_file", ""),
            "file_path":   doc.metadata.get("file_path", ""),
            "page_num":    doc.metadata.get("page_num", 0),
            "file_ext":    doc.metadata.get("file_ext", ""),
        }
        for doc in results
    ]

    span = mlflow.get_current_active_span()
    if span:
        span.set_attributes({
            "candidate_page_count":    len(candidate_pages),
            "retrieved_page_count":    len(retrieved),
            "restrict_to_candidates":  restrict_to_candidates,
            "query":                   exigence[:200],
        })

    logger.info(f"Semantic search: retrieved {len(retrieved)} page(s)")
    return retrieved
