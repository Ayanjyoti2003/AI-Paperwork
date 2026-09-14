# Paperwork Agent

An evidence-first AI assistant and administrative verification engine designed to guide users through complex paperwork requirements. Paperwork Agent transforms an administrative goal into a requirement plan, searches local documents for necessary evidence, extracts facts with exact provenance, performs deterministic rule verification, detects cross-document discrepancies, and delivers an actionable readiness assessment.

---

## Why It Exists

Administrative paperwork is confusing and time-consuming because applicants often do not know:
- Which specific documents are required for a particular goal.
- Whether their existing files meet government or institutional standards.
- Whether conflicting information exists across different documents (e.g. mismatched dates of birth or names).
- What evidence is still missing before submission.
- Whether their application package is actually complete and ready.

---

## What It Does

- **Natural Language Goal Matching:** Matches user goals (e.g., *"I want to complete the example application."*) to formal workflow requirements.
- **Local Document Vault & Upload:** Allows users to upload and manage documents (`.pdf`, `.txt`, `.md`, `.json`) stored safely in a controlled local store.
- **Targeted Evidence Retrieval:** Searches and reads only the specific documents needed for each requirement, avoiding dumping entire vaults into the LLM context.
- **Fact Extraction with Provenance:** Extracts structured fields with source document IDs and verbatim snippets.
- **Authoritative Deterministic Verification:** Evaluates evidence against workflow rules to classify each requirement as `satisfied`, `missing`, `conflict`, or `uncertain`.
- **Cross-Document Conflict Detection:** Automatically flags discrepancies when different documents present contradictory data.
- **Readiness Assessment & Action Plan:** Generates an overall readiness score, lists missing items, highlights conflicts, and suggests clear next steps for the user.

---

## How It Works: The Evidence-First Pipeline

Traditional AI workflows frequently feed entire document folders into an LLM context window, risking privacy leaks, high token costs, and hallucinations.

Paperwork Agent adopts an **evidence-first architecture**:
1. **Goal Discovery:** The agent discovers the matching administrative workflow.
2. **Requirements Loading:** The agent loads the precise requirements and accepted evidence types.
3. **Document Discovery:** Available local documents are discovered via metadata inspection.
4. **Targeted Search & Read:** The agent searches keyword snippets and reads only promising documents.
5. **Fact Extraction:** Structured facts are pulled with document provenance.
6. **Authoritative Verification:** Deterministic logic validates evidence, identifies gaps, and catches discrepancies.
7. **Readiness Assessment:** A structured, validated assessment is delivered to the user for human review.

---

## Architecture

```text
                        USER
                          │
                          ▼
                   NEXT.JS FRONTEND
              (Vault UI · Composer · Dashboard)
                          │
                          │ HTTP / JSON / multipart
                          ▼
                     FASTAPI API
                          │
                          ▼
                    STRANDS AGENT
          (or Deterministic Assessment Engine)
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
   WORKFLOW TOOLS   DOCUMENT TOOLS   VERIFY TOOLS
  - discover_workflow - list_documents - verify_requirements
  - get_requirements  - search_documents
                      - read_document
                      - extract_document_facts
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
             LOCAL FILE STORE    FACT EXTRACTION
           (data/documents/)   (Exact Provenance)
                    │                   │
                    └─────────┬─────────┘
                              ▼
                     READINESS RESULT
                    (Score · Checks · Actions)
                              │
                              ▼
                        HUMAN REVIEW
                              │
                              ▼
                      PAPERWORK PACKAGE
```

---

## Document Pipeline

```text
Upload (multipart/form-data)
  │
  ▼
Validation (Extension check: .pdf, .txt, .md, .json | Max size: 10MB)
  │
  ▼
Sanitization & Local Storage (Safe filenames, collision prevention)
  │
  ▼
Document Discovery (list_documents)
  │
  ▼
Targeted Search & Text Extraction (search_documents / PyPDF2 / read_document)
  │
  ▼
Fact Extraction with Provenance (extract_document_facts)
  │
  ▼
Rule Verification & Cross-Document Conflict Detection (verify_requirements)
  │
  ▼
Readiness Assessment (ReadinessAssessment Pydantic model)
```

---

## Deterministic vs. LLM-Assisted Verification

- **Deterministic Verification Engine:** Rule evaluation, cross-document comparison, status classification (`satisfied`, `missing`, `conflict`, `uncertain`), and completion percentages are computed authoritatively by deterministic Python logic (`backend/app/tools/verification.py`). This guarantees zero hallucination for requirement checks.
- **LLM Agent Orchestration:** When API keys (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`) are present, a Strands Agent orchestrates dynamic tool selection and natural language goal resolution. If keys are omitted or offline, the backend seamlessly runs the deterministic assessment engine without fabricating mock LLM calls.

---

## Human Review & Safety Boundary

Paperwork Agent is designed to assist the user in preparing paperwork. It does **not** autonomously submit forms to government portals or bypass human validation. The prepared assessment is presented for explicit human review before any application package is finalized.

---

## Tech Stack

- **Frontend:**
  - Next.js 16 (Turbopack, App Router)
  - React 19
  - TypeScript
  - Tailwind CSS 4
- **Backend:**
  - FastAPI
  - Python 3.10+
  - Pydantic v2
  - Strands Agents SDK
  - PyPDF2
  - Uvicorn
- **Testing:**
  - Pytest
  - FastAPI TestClient

---

## Project Structure

```text
AI-Paperwork/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── agent.py               # Strands Agent setup & deterministic assessment fallback
│   │   ├── api.py                 # FastAPI endpoints (health, workflows, documents, upload, assess)
│   │   ├── prompts.py             # Agent system prompt and instructions
│   │   ├── schemas.py             # Pydantic models (Document, Fact, Assessment, UploadResponse)
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── documents.py       # list_documents, search_documents, read_document, extract_document_facts
│   │       ├── requirements.py    # discover_workflow, get_workflow_requirements
│   │       └── verification.py    # Deterministic rule engine & conflict detector
│   ├── data/
│   │   ├── documents/             # Controlled local document store (.txt, .pdf, .md, .json)
│   │   └── workflows/             # Workflow definitions (e.g., example_application.json)
│   ├── tests/
│   │   ├── conftest.py            # Path resolution
│   │   ├── test_agent.py          # Strands agent & model configuration tests
│   │   ├── test_api.py            # API endpoint integration & upload tests
│   │   └── test_tools.py          # Deterministic tool unit tests
│   ├── demo.py                    # End-to-end deterministic demonstration script
│   ├── run_agent.py               # Interactive CLI entry point
│   ├── requirements.txt           # Python dependencies
│   └── .env.example               # Environment template
├── frontend/
│   ├── app/
│   │   ├── applications/          # Applications list & passport details
│   │   ├── dashboard/             # Main overview dashboard
│   │   ├── documents/             # Document Vault & upload UI
│   │   ├── new-request/           # Interactive request composer & assessment display
│   │   ├── settings/              # Workspace privacy settings
│   │   ├── globals.css            # Styles
│   │   ├── layout.tsx             # Root layout & navigation shell
│   │   └── page.tsx               # Redirect to dashboard
│   ├── components/                # Modular React components
│   │   ├── app-shell.tsx          # Navigation sidebar & header
│   │   ├── document-row.tsx       # Document item with metadata and actions
│   │   ├── request-composer.tsx   # Goal input, live assessment triggers, and results
│   │   ├── upload-zone.tsx        # Drag-and-drop & file picker upload component
│   │   └── ui/                    # Card, Progress, StatusPill
│   ├── lib/
│   │   ├── api.ts                 # Typed API client for FastAPI backend
│   │   ├── data.ts                # Application mock templates
│   │   └── types.ts               # Shared TypeScript interfaces
│   ├── package.json               # Frontend dependencies & scripts
│   └── tsconfig.json              # TypeScript configuration
├── README.md                      # Project documentation
└── LICENSE                        # MIT License
```

---

## Setup & Local Execution

### 1. Backend Setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Variables

Create `.env` inside `backend/` from `.env.example`:

```bash
cp .env.example .env
```

| Variable | Default | Description |
| :--- | :--- | :--- |
| `MODEL_PROVIDER` | `openai` | LLM provider (`openai` or `anthropic`) |
| `MODEL_ID` | `gpt-4o` | Model identifier |
| `OPENAI_API_KEY` | - | OpenAI API key (optional for deterministic mode) |
| `ANTHROPIC_API_KEY`| - | Anthropic API key (optional for deterministic mode) |
| `MAX_UPLOAD_SIZE_MB`| `10` | Maximum file upload size in MB |
| `DOCUMENTS_DIR` | `data/documents` | Storage path for uploaded user documents |

### 3. Running the Backend API

```bash
# From backend directory:
uvicorn app.api:app --reload --port 8000
```

The interactive API documentation is available at `http://localhost:8000/docs`.

### 4. Frontend Setup & Execution

```bash
cd frontend

# Install Node dependencies
npm install

# Start local development server
npm run dev
```

Open `http://localhost:3000` in your browser.

---

## Running Tests

### Backend Tests (Pytest)

```bash
cd backend
python -m pytest -v
```

### End-to-End Deterministic Demo

```bash
cd backend
python demo.py
```

### Frontend Build & Lint Verification

```bash
cd frontend
npm run lint
npm run build
```

---

## API Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Service health status check |
| `GET` | `/api/workflows` | List registered workflow definitions |
| `GET` | `/api/documents` | List documents available in the local vault |
| `POST`| `/api/documents/upload`| Upload a document (`.pdf`, `.txt`, `.md`, `.json`) via `multipart/form-data` |
| `DELETE`| `/api/documents/{id}`| Remove a document from the local store by ID |
| `POST`| `/api/assess` | Run paperwork readiness assessment on a user goal |

---

## Privacy & Security

- **Controlled Local Storage:** Uploaded files are stored exclusively on the local filesystem in `backend/data/documents/`.
- **Upload Sanitization:** Filenames are sanitized, path traversal sequences (`../`, `/`, `\`) are stripped, and extensions are restricted to supported formats.
- **Evidence-First Minimization:** The system extracts and passes only relevant text snippets rather than uploading entire folders into an LLM context.
- **No Autonomous Submissions:** Consequential actions remain in the user's hands.

---

## Current Limitations

- **OCR Scope:** PDF text extraction uses `PyPDF2`. Scanned image PDFs requiring advanced OCR (Tesseract / Vision API) currently fall back gracefully with a notification.
- **Storage Scope:** Uses private local filesystem storage; production multi-user database storage is not currently implemented.
- **Workflow Registry:** Workflows are loaded from local JSON schemas in `backend/data/workflows/`.

---

## Future Work

- **Optical Character Recognition (OCR):** Integration with a dedicated OCR engine for scanned image PDFs and physical camera captures.
- **User Authentication & Multi-Tenancy:** Secure user accounts with isolated private vaults.
- **Encrypted Document Storage:** At-rest encryption for sensitive user files.
- **Browser-Assisted Portal Filling:** Interactive form autofill assistance with human confirmation step.
- **Expanded Workflow Library:** Visa applications, tax exemption forms, university admissions, and local licensing workflows.
