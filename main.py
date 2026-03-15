"""
main.py — HR Candidate Document Verification Pipeline entry point.

Usage:
    python main.py

What it does:
    1. Loads all PDF and Markdown files from the candidate's proof folder (once)
    2. Reads the document checklist from the HR verification Excel
    3. For each required document, runs the 3-stage LangGraph pipeline:
           BM25 triage → semantic page search → LLM verdict
    4. Writes the verdicts back into the Excel (Statut, Commentaires columns)
"""
import logging
import sys

from config import EXCEL_INPUT, EXCEL_OUTPUT, PROOF_FOLDER, validate_config
from pipeline.graph import build_compliance_graph
from pipeline.ingestion import load_proof_folder
from utils.excel_handler import read_document_checklist, write_results

# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)-8s]  %(name)s — %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("=" * 60)
    logger.info("  HR Document Verification — RAG Pipeline")
    logger.info("=" * 60)

    # ── 0. Validate environment ──────────────────────────────────────────────
    try:
        validate_config()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    # ── 1. Load candidate documents (expensive step — done only once) ────────
    logger.info(f"\n[Step 1] Loading candidate documents from: {PROOF_FOLDER}")
    file_corpus = load_proof_folder(PROOF_FOLDER)

    if not file_corpus:
        logger.error("No documents found. Check that the proof folder exists and contains PDF or Markdown files.")
        sys.exit(1)

    logger.info(f"Corpus ready: {len(file_corpus)} document(s)\n")

    # ── 2. Read document checklist from the HR Excel ─────────────────────────
    logger.info(f"[Step 2] Reading document checklist from: {EXCEL_INPUT}")
    checklist = read_document_checklist(EXCEL_INPUT)

    if not checklist:
        logger.error("No document requirements found. Check the Excel file path and format.")
        sys.exit(1)

    required_count  = sum(1 for r in checklist if r["is_required"])
    optional_count  = len(checklist) - required_count
    logger.info(f"Found {len(checklist)} document(s): {required_count} required, {optional_count} optional\n")

    # ── 3. Build the LangGraph pipeline (compiled once, reused per row) ──────
    logger.info("[Step 3] Compiling LangGraph pipeline...")
    graph = build_compliance_graph()
    logger.info("Pipeline ready\n")

    # ── 4. Run the pipeline for each document in the checklist ───────────────
    logger.info(f"[Step 4] Verifying {len(checklist)} document(s)...\n")
    results = []

    for i, row in enumerate(checklist, 1):
        req_label = "REQUIRED" if row["is_required"] else "optional"
        logger.info(f"{'─' * 55}")
        logger.info(f"[{i}/{len(checklist)}] [{req_label}] {row['doc_fr']}")

        initial_state = {
            "doc_fr":          row["doc_fr"],
            "doc_en":          row["doc_en"],
            "file_corpus":     file_corpus,
            # Filled by graph nodes:
            "french_keywords": [],
            "candidate_pages": [],
            "retrieved_pages": [],
            "verdict":         {},
        }

        final_state = graph.invoke(initial_state)

        results.append({
            "doc_fr":      row["doc_fr"],
            "is_required": row["is_required"],
            "verdict":     final_state["verdict"],
        })

    # ── 5. Write results back into the HR Excel ───────────────────────────────
    logger.info(f"\n{'─' * 55}")
    logger.info(f"[Step 5] Writing results to: {EXCEL_OUTPUT}")
    write_results(EXCEL_INPUT, EXCEL_OUTPUT, results)

    # ── Summary ──────────────────────────────────────────────────────────────
    found    = sum(1 for r in results if r["verdict"].get("satisfied"))
    missing  = sum(1 for r in results if not r["verdict"].get("satisfied") and r["is_required"])
    optional = sum(1 for r in results if not r["verdict"].get("satisfied") and not r["is_required"])

    logger.info(f"\n{'=' * 60}")
    logger.info(f"  ✅ Found    : {found}")
    logger.info(f"  ❌ Missing  : {missing} required document(s)")
    logger.info(f"  N/A        : {optional} optional document(s) not submitted")
    logger.info(f"  Results saved to: {EXCEL_OUTPUT}")
    logger.info(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
