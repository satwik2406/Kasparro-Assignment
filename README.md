# AI Resume Screeening and Ranking System
*(Kasparro assignment)*

> Production-minded, explainable screening and ranking pipeline for SDE Intern candidates with Python & AI/Agentic systems background.

---

## 📌 Executive Summary

This system ingests batches of resumes (PDF, DOCX, TXT), enforces strict hard eligibility filtering (Python stack + genuine AI/agentic project exposure), scores candidates across a calibrated 100-point rubric, enriches profiles with live public GitHub telemetry, and produces ranked shortlists backed by explainable evidence and penalty tracking.

```
📁 Resumes Folder (PDF, DOCX, TXT)
       │
       ▼
[ Resilient Document Ingestion & Parsers ] ──► Graceful error isolation (0-byte/corrupt files)
       │
       ▼
[ Hard Eligibility Filter ] ──────────────► Rejects non-Python / non-AI profiles with reasons
       │ (Eligible Only)
       ▼
[ Async GitHub Enrichment ] ──────────────► Live public repos, commits, 90-day activity (capped at 10 pts)
       │
       ▼
[ Hybrid 100-Point Scoring Engine ] ──────► Penalizes thin wrappers (-12 pts) & tutorial copies (-8 pts)
       │
       ▼
[ Shortlist Ranking & Structured Export ] ─► Pretty Rich CLI Table, JSON, CSV & FastAPI (/screen, /results)
```

---

## 🚀 Quickstart

### 1. Prerequisites & Environment Setup
- Python 3.10+ (Tested on Python 3.12)
- Virtual environment:

```bash
# Clone or navigate to the repository
cd ai-resume-screener

# Create and activate virtual environment
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables (Optional)
Copy `.env.example` to `.env` if you wish to configure API keys:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `GITHUB_TOKEN` | Optional | Personal access token. Increases GitHub API rate limit from 60 to 5,000 req/hr. |
| `GEMINI_API_KEY` | Optional | Google Gemini API key for semantic scoring. |
| `OPENAI_API_KEY` | Optional | OpenAI API key for semantic scoring. |
| `MAX_CONCURRENT_REQUESTS` | Optional | Bounded concurrency worker limit (default: `5`). |

> **Note**: The system includes a high-precision, deterministic explainable rubric engine that operates out of the box with **zero API keys required**. If no LLM API key is present or network limits are exceeded, it executes with 100% stability.

---

## 💻 Running the Application

### Option A: Command-Line Interface (CLI)

Run screening against candidate resumes:

```bash
python main.py --input ./resumes --output ./output/results.json --csv ./output/results.csv
```

CLI Flags:
- `--input, -i`: Path to resumes directory (default: `./resumes`)
- `--output, -o`: Output path for JSON results (default: `./output/results.json`)
- `--csv`: Optional output path for CSV export
- `--concurrency, -c`: Max concurrent parsing and network tasks (default: `5`)
- `--serve`: Starts the FastAPI server instead of running CLI

### Option B: FastAPI Interface

Launch the interactive API server:

```bash
python main.py --serve --port 8000
```
or directly via Uvicorn:
```bash
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

Interactive Swagger documentation is available at: [http://localhost:8000/docs](http://localhost:8000/docs)

**API Endpoints:**
- `POST /screen`: Ingests and processes resumes directory.
  ```json
  {
    "input_dir": "./resumes",
    "output_file": "./output/results.json",
    "max_concurrency": 5
  }
  ```
- `GET /results`: Returns the latest screening report.
- `GET /health`: Returns service health and configuration details.

---

## 🧪 Running the Test Suite

A comprehensive test suite of 20 unit and integration tests covers parsers, eligibility rules, scoring penalties, GitHub enrichment caching, and FastAPI endpoints:

```bash
pytest -v
```

---

## 📊 100-Point Scoring Rubric

The 100-point rubric is balanced across five key dimensions:

| Category | Weight | Evaluation Criteria |
|---|:---:|---|
| **AI / Agentic / RAG Project Depth** | **40** | Stateful agents, LangGraph/CrewAI, RAG pipelines, vector databases (Qdrant/Pinecone/Chroma), tool/function calling, evaluation (Ragas/TruLens). |
| **Python & Backend Engineering** | **30** | Python, FastAPI, AsyncIO, PostgreSQL, Redis, SQLAlchemy. Rewards real project implementations over keyword lists. |
| **Cloud / Deployment / Full Stack** | **15** | Docker containerization, GCP/AWS deployment, CI/CD. React/Next.js are rewarded when part of an end-to-end full stack system. |
| **GitHub Activity** | **10** | Recent public commit activity (0-5 pts) + maintained relevant Python/AI repositories (0-5 pts). Missing GitHub never fails a candidate. |
| **Engineering Depth Signals** | **5** | Automated testing (pytest), caching, message queues (RabbitMQ/Celery), observability, and failure handling. |

### Strict Project-Quality Penalties
- **Thin LLM Wrapper Penalty (-12 pts)**: Deducted when an "AI project" is merely a trivial API call wrapper (e.g. prompt-in prompt-out Streamlit toy with no retrieval, tools, state, or business logic).
- **Tutorial Project Penalty (-8 pts)**: Deducted for cloned tutorial boilerplate (e.g. YouTube video summarizer clone, basic Udemy walkthroughs) lacking architectural ownership.

---

## 📁 Repository Structure

```
ai-resume-screener/
├── resumes/                    # Benchmark dataset of 50 synthetic candidate resumes
├── output/                     # Generated results.json and results.csv
├── src/
│   ├── __init__.py
│   ├── config.py               # Pydantic settings & environment configuration
│   ├── models.py               # Strict Pydantic schemas (parsed, eligibility, scores)
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py             # Base parser interface
│   │   ├── pdf_parser.py       # pypdf parser with corrupted byte isolation
│   │   ├── docx_parser.py      # python-docx parser for Word documents
│   │   ├── txt_parser.py       # Plain text parser with multi-encoding fallback
│   │   └── extractor.py        # Entity & contact extraction (regex + heuristics)
│   ├── filters/
│   │   ├── __init__.py
│   │   └── eligibility.py      # Deterministic hard eligibility filter rules
│   ├── enrichment/
│   │   ├── __init__.py
│   │   └── github.py           # Async GitHub API client, activity scoring & caching
│   ├── scoring/
│   │   ├── __init__.py
│   │   ├── rubric.py           # Rubric weights and penalty constants
│   │   └── scorer.py           # Hybrid & deterministic explainable scoring engine
│   ├── llm/
│   │   ├── __init__.py
│   │   └── adapter.py          # Provider-agnostic adapter (Gemini / OpenAI / fallback)
│   ├── pipeline.py             # Pipeline orchestrator with bounded concurrency
│   └── api.py                  # FastAPI application (/screen, /results, /health)
├── tests/                      # 20 unit and integration tests
├── scripts/
│   └── generate_synthetic_resumes.py # Generates 50 benchmark candidate resumes
├── main.py                     # CLI and FastAPI entry point
├── requirements.txt            # Production dependencies
├── pyproject.toml              # Build & pytest configuration
├── .env.example                # Example environment configuration
└── README.md                   # Complete documentation
```

---

## 📐 Design Decisions

### 1. Filtering Strategy (Hard Eligibility)
- **Why Outside the LLM?** Deterministic hard filtering outside the LLM ensures 100% reproducibility, zero token cost for non-viable candidates, and immune to prompt hallucination.
- **Rules Applied:**
  1. **Python Evidence:** Python must appear in skills, project technologies, or professional experience. Candidates with Java, C#, or React only are rejected immediately.
  2. **AI/Agentic Evidence:** Must demonstrate exposure to modern AI/agentic frameworks (LangGraph, CrewAI, LlamaIndex, LangChain) or concepts (RAG, vector search, embeddings, tool-calling, LLM evaluation).
  3. **Polyglot Safety:** Candidates with Java/React *in addition* to Python and AI projects are **not rejected**.
  4. **Explicit Rejection Output:** Ineligible candidates are tagged with explicit reasons (e.g. `"No evidence of Python stack"`, `"No AI/agentic project evidence"`).

### 2. Scoring Strategy & Penalty Mechanics
- **Evidence-Based Scoring:** Candidate scores reflect genuine architectural complexity rather than keyword stuffing. Projects featuring stateful agents, hybrid vector retrieval, and automated evaluation receive top tier AI depth scores.
- **Automated Penalty Application:** Rather than assigning passing scores to trivial OpenAI API calls, the system explicitly detects thin prompt wrappers and tutorial clones, deducts points (5–15 points), and surfaces the rationale in `applied_penalties`.
- **Capped Composite Score:** Category scores are strictly clamped to their rubric bounds and sum to a maximum of 100.

### 3. LLM Usage & Resilient Fallback
- **Structured Schema:** Uses Pydantic schemas enforcing exact integer score ranges, string summaries, and structured lists for strengths and concerns.
- **Provider Agnostic Adapter:** Cleanly abstracts Google Gemini and OpenAI derrière a unified interface.
- **Zero-Crash Fallback:** If an LLM call fails, times out, or no API key is provided, the system seamlessly transitions to its deterministic rule-based scorer. Individual resume failures never crash the batch.

### 4. GitHub Enrichment & Telemetry
- **Signals Extracted:** 90-day public commit/event count (0–5 pts) and maintained/relevant non-fork repositories with Python/AI topics (0–5 pts).
- **Graceful Degradation:** Private accounts, non-existent usernames (404), or rate limits (403/429) log an informational summary and award 0 points without penalizing the candidate or halting the run.
- **In-Memory Caching:** Prevents redundant network calls if usernames repeat across candidates.

---

## 🔮 If I Had More Time

1. **Hybrid Semantic Chunking & Vector Reranking for Resumes:**
   Incorporate a lightweight local embedding model (e.g., `all-MiniLM-L6-v2`) to compute semantic cosine similarity between candidate project descriptions and our target SDE Intern job spec, followed by a cross-encoder reranker for fine-grained ranking.
2. **Deep GitHub Repo Code Inspection:**
   Beyond counting repos, fetch the AST or tree of the candidate's top pinned Python repo to inspect code quality metrics: type hinting coverage (`mypy`), docstring completeness, test coverage (`pytest` presence), and git commit message hygiene.
3. **Automated Candidate Dossier PDF Generator:**
   Generate a downloadable 1-page executive summary PDF for each shortlisted candidate featuring a radar chart comparing their score breakdown against cohort averages, ideal for interview panels.
4. **OCR Pipeline for Scanned PDF Resumes:**
   Integrate Tesseract OCR or pdf2image fallback to extract text from purely scanned image-based PDF resumes that lack native text streams.
