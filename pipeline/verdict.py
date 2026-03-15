"""
pipeline/verdict.py — LLM-based document presence verdict.

Takes the retrieved pages and asks Groq's LLM whether they contain
the candidate document being searched for.

Also exposes generate_french_keywords() which is called by the
keyword_suggestion graph node (Node 1) to produce typical French
keywords for a given document type. These keywords are then fed
into both the BM25 query (Node 2) and this verdict prompt (Node 4).

Output schema (DocumentVerdict):
    satisfied    : bool           — Is the document present in the retrieved pages?
    confidence   : high/medium/low
    justification: str            — 2-3 sentence explanation
    source_file  : str            — File name where the document was found
    source_page  : int            — Page number (0 if N/A)
"""
import logging
from typing import Dict, List, Literal, Optional

import mlflow
from langchain_core.prompts import ChatPromptTemplate
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
        "Liste 20 à 30 mots-clés, expressions typiques, ET synonymes que l'on trouve dans un document "
        "de type '{doc_fr}' (en anglais : '{doc_en}'). "
        "Ces mots-clés seront utilisés pour rechercher ce document dans des fichiers texte via BM25. "
        "IMPORTANT : Tu dois inclure des synonymes directs du nom du document (ex: pour 'titre de séjour', inclure 'carte de séjour', 'permis de séjour', 'visa', etc.). "
        "Inclure aussi : intitulés de sections, mentions légales, termes administratifs courants.",
    ),
])


@mlflow.trace(name="generate_french_keywords", span_type="LLM")
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
        span = mlflow.get_current_active_span()
        if span:
            span.set_attributes({
                "doc_fr":        doc_fr,
                "doc_en":        doc_en,
                "keyword_count": len(keywords),
                "keywords":      ", ".join(keywords),
            })
        return keywords
    except Exception as e:
        logger.warning(f"[Keywords] Keyword generation failed for '{doc_fr}': {e}")
        return []


# ─── Verdict Prompt ───────────────────────────────────────────────────────────

VERDICT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
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
    ),
])


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

    Returns:
        Dict with keys: satisfied, confidence, justification, source_file, source_page
    """
    chain   = VERDICT_PROMPT | _build_llm().with_structured_output(DocumentVerdict)
    context = _format_context(retrieved_pages)
    keywords_section = _format_keywords(french_keywords or [])

    try:
        verdict: DocumentVerdict = chain.invoke({
            "doc_fr":          doc_fr,
            "doc_en":          doc_en,
            "context":         context,
            "keywords_section": keywords_section,
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
