"""
pipeline/verdict.py — LLM-based document presence verdict.

Takes the retrieved pages and asks Groq's LLM whether they contain
the candidate document being searched for.

<<<<<<< HEAD
Also exposes generate_french_keywords() which is called by the
keyword_suggestion graph node (Node 1) to produce typical French
keywords for a given document type. These keywords are then fed
into both the BM25 query (Node 2) and this verdict prompt (Node 4).

=======
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897
Output schema (DocumentVerdict):
    satisfied    : bool           — Is the document present in the retrieved pages?
    confidence   : high/medium/low
    justification: str            — 2-3 sentence explanation
    source_file  : str            — File name where the document was found
    source_page  : int            — Page number (0 if N/A)
"""
import logging
<<<<<<< HEAD
from typing import Dict, List, Literal, Optional

from langchain_core.prompts import ChatPromptTemplate
=======
from typing import Dict, List, Literal

from langchain.prompts import ChatPromptTemplate
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field

from config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

# Maximum characters taken from each retrieved page to avoid token overflow
MAX_CHARS_PER_PAGE = 1500


# ─── Output Schema ────────────────────────────────────────────────────────────

class DocumentVerdict(BaseModel):
    """Structured verdict returned by the LLM for one required document."""

    satisfied: bool = Field(
        description=(
            "True if the retrieved pages clearly contain the document being searched for "
            "(e.g. a CV, a residence permit, a social security card). "
            "False if the document is absent, unrelated, or unreadable."
        )
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description=(
            "high   → document clearly present or clearly absent. "
            "medium → partial match or document type is ambiguous. "
            "low    → could not determine (poor quality, unreadable, or no pages retrieved)."
        )
    )
    justification: str = Field(
        description=(
            "2-3 sentences explaining why the document is or is not considered present. "
            "Mention specific details found (name, date, issuer) or explain what is missing."
        )
    )
    source_file: str = Field(
        description="File name that contains the document, or 'N/A' if not found."
    )
    source_page: int = Field(
        description="Page number where the document was found in source_file. Use 0 if N/A."
    )


<<<<<<< HEAD
# ─── LLM builder ──────────────────────────────────────────────────────────────

def _build_llm(temperature: float = 0) -> ChatGroq:
    return ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=temperature)


# ─── Keyword Generation ───────────────────────────────────────────────────────

_KEYWORD_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "Tu es un expert en ressources humaines et en documents administratifs français. "
        "Réponds uniquement avec une liste de mots-clés séparés par des virgules, sans explication.",
    ),
    (
        "human",
        "Liste 12 à 15 mots-clés ou expressions typiques que l'on trouve dans un document "
        "de type '{doc_fr}' (en anglais : '{doc_en}'). "
        "Ces mots-clés seront utilisés pour rechercher ce document dans des fichiers texte. "
        "Inclure : intitulés de sections, mentions légales, termes administratifs courants.",
    ),
])


def generate_french_keywords(doc_fr: str, doc_en: str) -> List[str]:
    """
    Ask the LLM to generate typical French keywords found in documents
    of the given type. Returns a list of keyword strings.

    Used by the keyword_suggestion graph node (Node 1).
    The keywords are subsequently used to:
      - Boost the BM25 query (Node 2)
      - Guide the verdict LLM (Node 4)

    Falls back to an empty list on any error so the pipeline never crashes.
    """
    try:
        chain = _KEYWORD_PROMPT | _build_llm(temperature=0.2)
        response = chain.invoke({"doc_fr": doc_fr, "doc_en": doc_en})
        raw = response.content.strip()
        keywords = [k.strip() for k in raw.split(",") if k.strip()]
        logger.info(
            f"[Keywords] Generated {len(keywords)} keyword(s) for '{doc_fr}': "
            f"{keywords[:5]}{'...' if len(keywords) > 5 else ''}"
        )
        return keywords
    except Exception as e:
        logger.warning(f"[Keywords] Keyword generation failed for '{doc_fr}': {e}")
        return []


# ─── Verdict Prompt ───────────────────────────────────────────────────────────
=======
# ─── Prompt ───────────────────────────────────────────────────────────────────
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897

VERDICT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
<<<<<<< HEAD
        """Tu es un assistant de vérification de documents RH.
Ta mission : déterminer si un document spécifique soumis par un candidat est présent
dans les extraits de fichiers fournis.

Règles :
- Marque TROUVÉ uniquement si le document correspond clairement au type recherché.
- Un document partiel ou expiré peut être marqué TROUVÉ, mais note le problème dans la justification.
- Si aucun extrait pertinent n'est fourni, marque NON TROUVÉ avec une faible confiance.
- Sois concis et factuel. Mentionne les détails clés trouvés (dates, noms, autorité émettrice).
- Réponds en français.""",
    ),
    (
        "human",
        """## Document recherché
Français : {doc_fr}
English  : {doc_en}

## Mots-clés typiques à rechercher
{keywords_section}

## Extraits de fichiers récupérés
{context}

---
Sur la base des extraits ci-dessus uniquement, ce document est-il présent dans les fichiers soumis par le candidat ?""",
=======
        """You are an HR document verification assistant.
Your task: determine whether a specific document submitted by a job candidate is present
in the provided file excerpts.

Rules:
- Mark as FOUND only if the document clearly matches the type being searched for.
- A partial or expired document should still be marked as FOUND, but note the issue in justification.
- If no relevant excerpt is provided, mark as NOT FOUND with low confidence.
- Be concise and factual. Mention any key details you found (dates, names, issuing authority).
- Respond in French.""",
    ),
    (
        "human",
        """## Document recherché (Document to find)
Français : {doc_fr}
English  : {doc_en}

## Extraits de fichiers récupérés (Retrieved File Excerpts)
{context}

---
Based solely on the excerpts above, is this document present in the candidate's submitted files?""",
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897
    ),
])


<<<<<<< HEAD
=======
# ─── Chain Builder ────────────────────────────────────────────────────────────

def _build_verdict_chain():
    """Build the LangChain chain: prompt → Groq LLM → structured DocumentVerdict."""
    llm = ChatGroq(
        api_key=GROQ_API_KEY,
        model=GROQ_MODEL,
        temperature=0,
    )
    return VERDICT_PROMPT | llm.with_structured_output(DocumentVerdict)


>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897
# ─── Context Formatter ────────────────────────────────────────────────────────

def _format_context(retrieved_pages: List[Dict]) -> str:
    """Format retrieved pages into a readable block for the LLM prompt."""
    if not retrieved_pages:
        return "⚠️  Aucun document pertinent trouvé dans le dossier candidat."

    blocks = []
    for i, page in enumerate(retrieved_pages, 1):
        text_preview = page["text"][:MAX_CHARS_PER_PAGE]
        if len(page["text"]) > MAX_CHARS_PER_PAGE:
            text_preview += "... [tronqué / truncated]"

        blocks.append(
            f"[Extrait {i}] Fichier : {page['source_file']} | Page : {page['page_num']}\n"
            f"{text_preview}"
        )

    return "\n\n" + ("\n\n" + "─" * 60 + "\n\n").join(blocks)


<<<<<<< HEAD
def _format_keywords(french_keywords: List[str]) -> str:
    """Format the keyword list into a prompt-friendly string."""
    if not french_keywords:
        return "(aucun mot-clé fourni)"
    return ", ".join(french_keywords)


# ─── Public API ───────────────────────────────────────────────────────────────

def run_verdict(
    doc_fr: str,
    doc_en: str,
    retrieved_pages: List[Dict],
    french_keywords: Optional[List[str]] = None,
) -> Dict:
    """
    Run the LLM verdict chain for a single document requirement.

    Args:
        doc_fr:          French document name.
        doc_en:          English document name.
        retrieved_pages: Pages retrieved by semantic search.
        french_keywords: Optional list of typical French keywords for this
                         document type (generated by keyword_suggestion node).
=======
# ─── Public API ───────────────────────────────────────────────────────────────

def run_verdict(doc_fr: str, doc_en: str, retrieved_pages: List[Dict]) -> Dict:
    """
    Run the LLM verdict chain for a single document requirement.

    The function signature uses doc_fr / doc_en instead of exigence / proof_type
    to match the HR use case. The graph node calls this via keyword arguments
    stored in the pipeline state.

    Falls back to a safe "not found" verdict on any exception so the pipeline
    never crashes mid-run.
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897

    Returns:
        Dict with keys: satisfied, confidence, justification, source_file, source_page
    """
<<<<<<< HEAD
    chain   = VERDICT_PROMPT | _build_llm().with_structured_output(DocumentVerdict)
    context = _format_context(retrieved_pages)
    keywords_section = _format_keywords(french_keywords or [])

    try:
        verdict: DocumentVerdict = chain.invoke({
            "doc_fr":          doc_fr,
            "doc_en":          doc_en,
            "context":         context,
            "keywords_section": keywords_section,
=======
    chain   = _build_verdict_chain()
    context = _format_context(retrieved_pages)

    try:
        verdict: DocumentVerdict = chain.invoke({
            "doc_fr":  doc_fr,
            "doc_en":  doc_en,
            "context": context,
>>>>>>> 0f909347a4ecb9caed3f0bdbe2602984c9e8a897
        })
        return verdict.model_dump()

    except Exception as e:
        logger.error(f"LLM verdict failed: {e}")
        return {
            "satisfied":     False,
            "confidence":    "low",
            "justification": f"Verdict non déterminé en raison d'une erreur : {e}",
            "source_file":   "N/A",
            "source_page":   0,
        }
