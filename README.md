# LearnPilot AI

AI-powered personal learning and teaching assistant that turns study materials into interactive learning experiences.

## Features

- Upload text-based PDFs and extract page-level text with PyMuPDF.
- Ask questions grounded in uploaded documents and view source filename/page citations.
- Retrieval-augmented generation (RAG) using Sentence Transformers and ChromaDB, with lexical retrieval fallback.
- Generate multiple-choice quizzes and flashcards from study material.
- Create a seven-day personalized learning roadmap.
- Generate teacher-oriented lesson plans and worksheets.
- Track uploaded documents and quiz analytics.
- Choose an LLM provider through environment configuration (Groq-compatible API or Gemini OpenAI-compatible endpoint).

## Stack

- **Frontend:** Next.js 15, React 19, TypeScript
- **API:** Python, FastAPI
- **PDF processing:** PyMuPDF
- **Retrieval:** Sentence Transformers, ChromaDB, lexical fallback
- **Persistence:** SQLAlchemy; SQLite by default
- **Container support:** Docker Compose (API and Redis service)

## Repository structure

```text
learnpilot-ai/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── ai.py
│   │   ├── vector_store.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── app/
│   ├── package.json
│   ├── tsconfig.json
│   └── .env.local.example
├── docker-compose.yml
└── README.md
```

## Run locally on Windows

### 1. Start the FastAPI backend

Open PowerShell:

```powershell
cd backend
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

API health check: http://localhost:8000/api/health  
Interactive API docs: http://localhost:8000/docs

### 2. Start the Next.js frontend

In a second terminal, from the repository root:

```powershell
cd frontend
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Open http://localhost:3000.

The frontend expects the API at `http://localhost:8000` by default. Change `NEXT_PUBLIC_API_URL` in `frontend/.env.local` if needed.

## Configure an LLM (optional)

The application can run in retrieval-demo mode without an API key. For a Groq-compatible provider, edit `backend/.env`:

```env
LLM_PROVIDER=groq
LLM_API_KEY=your_groq_api_key
LLM_MODEL=llama-3.3-70b-versatile
LLM_BASE_URL=https://api.groq.com/openai/v1
```

For Gemini, set `LLM_PROVIDER=gemini`, your API key, and a model supported by the configured Gemini endpoint.

**Never commit API keys, credentials, or real user documents.** The `.env` files are local configuration files; only the example templates belong in Git.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Service health and LLM configuration |
| GET | `/api/documents` | List uploaded documents |
| POST | `/api/documents/upload` | Upload a PDF |
| DELETE | `/api/documents/{id}` | Delete a document |
| POST | `/api/chat` | Ask a grounded question |
| POST | `/api/quiz` | Generate quiz questions |
| POST | `/api/flashcards` | Generate flashcards |
| POST | `/api/roadmap` | Generate a seven-day plan |
| POST | `/api/teacher/lesson-plan` | Generate lesson-plan content |
| GET | `/api/analytics` | Read simple learning analytics |

## Current limitations

This is an MVP for local development, not a production-ready learning platform. It does not currently include authentication, authorization, OCR for scanned PDFs, robust background ingestion, formal database migrations, or production-grade monitoring. Validate uploaded files and generated educational content before using the system with real users. The embedding model may download on first use and can require additional memory and startup time.

## Roadmap

- Add authentication, user-specific document isolation, and authorization.
- Add OCR for scanned PDFs and more robust file validation.
- Improve chunking, hybrid retrieval, reranking, and citation verification.
- Add automated RAG evaluation for faithfulness and retrieval quality.
- Add spaced repetition, learner history, adaptive difficulty, and background jobs.
- Add automated tests and production deployment configuration.

## License

No license has been specified yet. Add a license file before redistributing the project.
