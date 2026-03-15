"""
config.py — Central configuration loaded from .env

All other modules import from here instead of calling os.getenv directly.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ─── LLM ─────────────────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ─── Embeddings ───────────────────────────────────────────────────────────────
EMBEDDING_MODEL: str = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

# ─── Retrieval Tuning ─────────────────────────────────────────────────────────
<<<<<<< HEAD
BM25_TOP_K: int = int(os.getenv("BM25_TOP_K", "10"))        # top-K pages shortlisted by BM25
=======
BM25_TOP_K: int = int(os.getenv("BM25_TOP_K", "5"))
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897
SEMANTIC_TOP_M: int = int(os.getenv("SEMANTIC_TOP_M", "3"))
MIN_TEXT_LENGTH: int = int(os.getenv("MIN_TEXT_LENGTH", "50"))

# ─── OCR ─────────────────────────────────────────────────────────────────────
OCR_LANGUAGES: str = os.getenv("OCR_LANGUAGES", "fra+eng")

# ─── Paths ────────────────────────────────────────────────────────────────────
PROOF_FOLDER: str = os.getenv("PROOF_FOLDER", "./proof")
EXCEL_INPUT: str = os.getenv("EXCEL_INPUT", "./hr_candidate_verification.xlsx")
EXCEL_OUTPUT: str = os.getenv("EXCEL_OUTPUT", "./hr_candidate_results.xlsx")

<<<<<<< HEAD
# ─── ChromaDB ───────────────────────────────────────────────────────────────────────────────────
# Folder where ChromaDB persists its on-disk store (created automatically)
CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
# Collection name — reused across runs so embeddings accumulate
CHROMA_COLLECTION_NAME: str = os.getenv("CHROMA_COLLECTION_NAME", "compliance_pages")
# When True, ChromaDB similarity search is restricted to BM25-shortlisted pages only
RESTRICT_SEARCH_TO_CANDIDATE_PAGES: bool = os.getenv("RESTRICT_SEARCH_TO_CANDIDATE_PAGES", "true").lower() == "true"

=======
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897

def validate_config() -> None:
    """Raise early if critical config is missing."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set. Please fill in your .env file.")
