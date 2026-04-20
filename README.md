# OMNIRRAG — Conflict-Aware RAG Pipeline

A retrieval-augmented generation pipeline that detects, debates, and resolves conflicts in retrieved evidence before generating a final answer. Goes beyond standard RAG by adding pairwise relation reasoning, credibility scoring, diversity-aware selection, and multi-agent debate.

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- An OpenAI API key

---

## 1. Clone the repository

```bash
git clone https://github.com/Vortexx-hash/OMNIRRAG.git
cd OMNIRRAG
```

---

## 2. Backend setup

### 2.1 Create and activate a virtual environment

```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 2.2 Install Python dependencies

```bash
pip install -r requirements.txt
```

> The first run will download the `all-MiniLM-L6-v2` sentence-transformers model (~90 MB). This happens automatically on startup.

### 2.3 Set your OpenAI API key

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=sk-...
```

### 2.4 Start the backend

```bash
python run_server.py
```

The API will be available at `http://localhost:8000`.

---

## 3. Frontend setup

### 3.1 Install Node dependencies

```bash
cd frontend
npm install
```

### 3.2 Start the dev server

```bash
npm run dev
```

The frontend will be available at `http://localhost:5173`.

---

## 4. Usage

1. Open `http://localhost:5173` in your browser.
2. Upload one or more documents (PDF or URL) using the upload panel.
3. Type a question in the search bar and hit send.
4. Watch the pipeline execute step by step — query normalisation, retrieval, relation building, DPP selection, agent debate, conflict analysis, and final synthesis.

---

## 5. Running tests

```bash
pytest tests/
```

---

## Project structure

```
├── main.py                  # Pipeline orchestrator
├── run_server.py            # Uvicorn entry point
├── api/                     # FastAPI routes and schemas
├── pipeline/
│   ├── upload/              # Chunker, embedder, vector store
│   ├── query/               # Normalizer, retriever
│   ├── relations/           # NLI, NER, similarity, relevance
│   ├── selection/           # DPP selector
│   ├── debate/              # Agent bank, orchestrator
│   ├── synthesis/           # Conflict report, answer synthesizer
│   └── shared/              # Constants, helpers, types
├── models/                  # Pydantic schemas
├── frontend/                # React + Vite + Tailwind UI
└── tests/                   # Pytest test suite
```
