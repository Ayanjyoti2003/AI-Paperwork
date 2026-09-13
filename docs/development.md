# Paperwork Agent Developer Guide

This guide provides practical instructions for setting up, developing, testing, and running Paperwork Agent locally.

---

## 1. System Prerequisites

The repository has been tested against the following baseline versions:
- **Python**: 3.10+ (tested on Python 3.13.5)
- **Node.js**: 18.0+ (tested on Node.js v22.17.1)
- **npm**: 9.0+ (tested on npm 11.4.2)
- **OS**: Windows, macOS, or Linux

---

## 2. Installation & Setup

### Step 1: Clone the Repository
```bash
git clone https://github.com/Ayanjyoti2003/AI-Paperwork.git
cd AI-Paperwork
```

### Step 2: Backend Setup
Create and activate a Python virtual environment:

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**On macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install backend dependencies:
```bash
pip install -r backend/requirements.txt
```

### Step 3: Environment Configuration
Copy the template configuration file:

**On Windows (PowerShell):**
```powershell
cp backend/.env.example backend/.env
```

**On macOS / Linux:**
```bash
cp backend/.env.example backend/.env
```

> **Note on API Keys**: An OpenAI or Anthropic API key is **optional**. If no key is configured, Paperwork Agent automatically executes its deterministic verification pipeline, enabling complete offline development, testing, and demonstration.

### Step 4: Frontend Setup
From the repository root, enter the frontend directory and install dependencies:
```bash
cd frontend
npm install
cd ..
```

---

## 3. Running the Application

### Option A: Running the Deterministic Demo (CLI)
You can run the end-to-end verification demo immediately without running any servers:

From the repository root:
```bash
python backend/demo.py
```

Or from the `backend/` directory:
```bash
cd backend
python demo.py
```

### Option B: Running the Interactive CLI Agent
To interact with the agent via command-line interface:
```bash
python backend/run_agent.py
```

### Option C: Running the Full Web Application

Start the **Backend API Server** (Port 8000):
```bash
python -m uvicorn app.api:app --reload --host 127.0.0.1 --port 8000
```
*(Run from the `backend/` directory or run `uvicorn backend.app.api:app --reload` from repository root)*

Start the **Next.js Web Frontend** (Port 3000):
```bash
cd frontend
npm run dev
```

Open your browser at:
- Web Application: `http://localhost:3000`
- Interactive API Docs (Swagger UI): `http://127.0.0.1:8000/docs`
- Alternative API Docs (ReDoc): `http://127.0.0.1:8000/redoc`

---

## 4. Testing & Verification

### Backend Automated Test Suite
The backend contains 82 automated unit, integration, and security tests:

From the `backend/` directory:
```bash
python -m pytest tests/ -v
```

From the repository root:
```bash
python -m pytest backend/tests/ -v
```

### Frontend Production Build Validation
Verify that the Next.js frontend builds without errors:
```bash
cd frontend
npm run build
```

---

## 5. Directory Layout & Data Stores

- **`backend/data/workflows/`**: JSON schema definitions for administrative workflows (e.g. `example_application.json`). Add new workflow definitions here to register them with the system.
- **`backend/data/documents/`**: User document storage directory. Demo documents (`identity.txt`, `address_proof.txt`, `certificate.txt`) are stored here. Uploaded files through the API or UI are safely deposited into this folder.
- **`backend/data/sample_documents/`**: Synthetic demonstration assets such as `identity_scan.png`.

---

## 6. Common Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| `ModuleNotFoundError: No module named 'app'` | Running backend commands outside `backend/` without `PYTHONPATH` | Run commands with `python -m pytest tests/` from inside `backend/`, or run `python backend/demo.py` from repo root (scripts automatically resolve sys.path). |
| `OPENAI_API_KEY is not set or placeholder` | Running live agent without valid key | Either provide a valid key in `backend/.env`, or rely on the deterministic pipeline which requires no credentials. |
| Port 8000 already in use | Another Uvicorn instance is running | Terminate the existing process or run on an alternate port: `uvicorn app.api:app --port 8001`. Update `NEXT_PUBLIC_API_URL` in frontend if changed. |
| Turbopack watch warnings on Windows | Windows file system locking | Standard Turbopack warning; builds and development server functionality are unaffected. |
