# Paperwork Agent

An intelligent AI assistant designed to verify and guide users through complex administrative paperwork workflows. It pairs natural language goal discovery with deterministic verification, strict cross-document conflict detection, and actionable readiness assessments.

---

## Repository Structure

```text
paperwork-agent/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── agent.py               # Strands Agent definition and tool orchestration
│   │   ├── api.py                 # FastAPI backend layer
│   │   ├── prompts.py             # System prompt and behavioral guidelines
│   │   ├── schemas.py             # Pydantic data models & assessment contracts
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── documents.py       # Document discovery, search, reading, and fact extraction
│   │       ├── requirements.py    # Workflow discovery and requirements loading
│   │       └── verification.py    # Authoritative deterministic verification & conflict engine
│   ├── data/
│   │   ├── documents/             # Local user documents store (.txt, .pdf, .md, .json)
│   │   └── workflows/             # Workflow schema definitions
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py            # Pytest path configuration
│   │   ├── test_agent.py          # Agent orchestration and model configuration tests
│   │   ├── test_api.py            # API endpoint integration tests
│   │   └── test_tools.py          # Deterministic verification and tool unit tests
│   ├── demo.py                    # End-to-end deterministic workflow demonstration
│   ├── run_agent.py               # Interactive CLI entry point
│   ├── requirements.txt           # Python backend dependencies
│   └── .env.example               # Environment variables template
├── frontend/                      # Web frontend application workspace
├── README.md                      # Repository documentation
├── LICENSE                        # MIT License
└── .gitignore                     # Repository-wide ignore rules
```

---

## Getting Started

### 1. Prerequisites
- Python 3.10+
- (Optional) An OpenAI or Anthropic API key for live LLM agent interactions. Deterministic verification, tests, and demo work entirely offline without an API key.

### 2. Installation

Install backend dependencies:

```bash
pip install -r backend/requirements.txt
```

### 3. Environment Configuration (Optional)

Copy the environment template:

```bash
cp backend/.env.example backend/.env
```

Configure your preferred LLM provider (`openai` or `anthropic`) and API key in `backend/.env` if running the live agent.

---

## Running the Backend

The backend is engineered to run reliably from **both** the repository root and the `backend/` directory.

### Option A: From Repository Root

- **Run Deterministic Demo:**
  ```bash
  python backend/demo.py
  ```

- **Run Complete Test Suite:**
  ```bash
  python -m pytest backend/tests/ -v
  ```

- **Run Interactive Agent CLI:**
  ```bash
  python backend/run_agent.py
  ```

- **Run FastAPI Server:**
  ```bash
  uvicorn backend.app.api:app --reload
  ```

### Option B: From Backend Directory

```bash
cd backend
```

- **Run Deterministic Demo:**
  ```bash
  python demo.py
  ```

- **Run Complete Test Suite:**
  ```bash
  python -m pytest tests/ -v
  ```

- **Run Interactive Agent CLI:**
  ```bash
  python run_agent.py
  ```

- **Run FastAPI Server:**
  ```bash
  uvicorn app.api:app --reload
  ```

---

## Frontend Development

The `frontend/` directory is reserved for the web UI. It operates independently and communicates with the backend API.

---

## License

This project is licensed under the [MIT License](LICENSE).
