# LearnPilot AI

AI-powered personal learning and teaching assistant that turns study materials into interactive learning experiences.

## Features

- Upload text-based PDFs with file-signature, size, and page-count validation.
- Ask questions grounded in uploaded documents with filename/page citations.
- RAG using Sentence Transformers and ChromaDB, with lexical fallback.
- Generate quizzes, flashcards, seven-day learning roadmaps, and teacher lesson plans.
- JWT registration/login and per-user document and quiz-event isolation.
- Quiz submission, scoring, and user-specific analytics.
- Document ingestion status with an explicit retry endpoint when vector indexing fails.

## Stack

- **Frontend:** Next.js 15, React 19, TypeScript
- **API:** Python, FastAPI
- **PDF processing:** PyMuPDF
- **Retrieval:** Sentence Transformers, ChromaDB, lexical fallback
- **Persistence:** SQLAlchemy; SQLite by default
- **Authentication:** JWT bearer tokens and PBKDF2 password hashing
- **CI:** GitHub Actions (backend tests and frontend build)

## Local setup (Windows PowerShell)

### Backend

```powershell
cd backend
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env` and replace `JWT_SECRET` with a long random secret before using the application beyond local development. Then start the API:

```powershell
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

In a second PowerShell terminal:

```powershell
cd frontend
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Open http://localhost:3000. Register an account on the sign-in screen. The frontend stores the access token in browser local storage and sends it as a bearer token for protected requests.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Service health |
| POST | `/api/auth/register` | Create an account |
| POST | `/api/auth/login` | Obtain a JWT |
| GET | `/api/auth/me` | Current account |
| GET | `/api/documents` | List the signed-in user's documents |
| POST | `/api/documents/upload` | Upload and index a PDF |
| POST | `/api/documents/{id}/retry-index` | Retry failed vector indexing |
| DELETE | `/api/documents/{id}` | Delete an owned document |
| POST | `/api/chat` | Ask a grounded question |
| POST | `/api/quiz` | Generate quiz questions |
| POST | `/api/events/quiz-result` | Save a quiz score |
| POST | `/api/flashcards` | Generate flashcards |
| POST | `/api/roadmap` | Generate a seven-day plan |
| POST | `/api/teacher/lesson-plan` | Generate lesson-plan content |
| GET | `/api/analytics` | User-specific learning analytics |

## Existing database migration note

`Base.metadata.create_all()` creates missing tables but does not add new columns to existing tables. This release adds `users`, `user_id`, document indexing status, and related fields. **Back up your existing database before upgrading.** For an existing local SQLite database, use a migration or start with a fresh database if the old data is not needed. Do not rely on automatic table creation to alter an existing schema. The startup bootstrap assigns legacy records with a null owner to a generated local legacy account; it does not provide a login for that legacy account.

## Tests

```powershell
cd backend
pip install -r requirements.txt
pytest -q
```

GitHub Actions runs backend tests and a frontend production build on pushes and pull requests targeting `main`.

## Configure an LLM (optional)

The application can run in retrieval-demo mode without an API key. For Groq-compatible configuration, set `LLM_PROVIDER=groq`, `LLM_API_KEY`, `LLM_MODEL`, and `LLM_BASE_URL` in `backend/.env`. Gemini can be configured with `LLM_PROVIDER=gemini` and a supported model/key.

**Never commit API keys, credentials, real user documents, or local databases.** Only example environment templates belong in Git.

## Current limitations

This is an MVP, not a production-ready learning platform. OCR for scanned PDFs, formal Alembic migrations, background ingestion workers, token refresh/revocation, email verification, password reset, production monitoring, and a hardened production secrets strategy are not implemented. The current indexing retry is synchronous. Review generated educational content before relying on it.

## Roadmap

- Alembic migrations and production database setup.
- Background ingestion workers and retry queues.
- Hybrid retrieval, reranking, citation verification, and RAG evaluation.
- Spaced repetition, learner history, adaptive difficulty, and topic mastery.
- OCR and production monitoring.

No license has been specified yet. Add a license file before redistributing the project.
