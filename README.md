# AI4DueDil — Compliance RAG Pipeline

A two-stage RAG system that checks whether documents in a `proof/` folder satisfy compliance requirements listed in an Excel file.

## Architecture

```
Excel (Exigence + Proof Type)
         │
         ▼
  [Stage 1 — BM25]          Lexical search over all files → shortlist top-K
         │
    top-K files
         │
         ▼
  [Stage 2 — ChromaDB]      Embed pages of shortlisted files → retrieve top-M pages
         │
    top-M pages
         │
         ▼
  [Stage 3 — Groq LLM]      Assess whether pages satisfy the requirement
         │
         ▼
  Excel output with ✅/❌ per row
```

## Setup

### 1. Install system dependencies (Tesseract OCR)

```bash
# Ubuntu / Debian
sudo apt-get install tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng

# macOS
brew install tesseract
brew install tesseract-lang  # for French support
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 4. Prepare your files

```
compliance_rag/
├── exigences.xlsx     ← your Excel file (Exigence + Preuve Attendue columns)
└── proof/
    ├── certificat_iso27001.pdf
    ├── attestation_fiscale.pdf
    ├── politique_securite.md
    └── ...
```

### 5. Run

```bash
python main.py
```

Results are saved to `results.xlsx` with 5 new columns added to the right.

## Project Structure

```
compliance_rag/
├── main.py                  ← Entry point
├── config.py                ← All env vars in one place
├── requirements.txt
├── .env.example
├── pipeline/
│   ├── ingestion.py         ← PDF/Markdown text extraction + OCR
│   ├── retrieval.py         ← BM25 triage + ChromaDB semantic search
│   ├── verdict.py           ← Groq LLM structured verdict chain
│   └── graph.py             ← LangGraph 3-node pipeline
└── utils/
    └── excel_handler.py     ← Read exigences, write results
```

## Tuning

| Variable | Default | Effect |
|---|---|---|
| `BM25_TOP_K` | 5 | More files checked in Stage 1 → better recall, slower Stage 2 |
| `SEMANTIC_TOP_M` | 3 | More pages sent to LLM → better recall, more tokens used |
| `MIN_TEXT_LENGTH` | 50 | Lower = more OCR fallbacks triggered |
| `GROQ_MODEL` | llama-3.3-70b-versatile | Swap for a faster/cheaper model if needed |
| `EMBEDDING_MODEL` | paraphrase-multilingual-MiniLM-L12-v2 | Good French/English balance |

## Supported File Types

| Type | Extraction Method |
|---|---|
| PDF (digital) | PyMuPDF — fast, accurate |
| PDF (scanned) | PyMuPDF → Tesseract OCR fallback (auto-detected) |
| Markdown | Plain text read |
