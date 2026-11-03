# LearnPilot AI

AI-powered personal learning and teaching assistant that turns study materials into interactive learning experiences.

## Features

- Upload PDF study materials and extract text page by page.
- Ask questions about uploaded material using retrieval-augmented generation (RAG).
- Receive answers with source filename and page references.
- Generate quizzes and flashcards from study content.
- Create a personalized seven-day learning plan.
- Use a teacher assistant workflow for educational content.
- Store application data with SQLAlchemy; SQLite is the default local database.
- Run the application locally or with Docker Compose.

## Tech Stack

**Frontend:** Next.js, React, TypeScript  
**Backend:** Python, FastAPI  
**Document processing:** PyMuPDF  
**Embeddings and vector search:** Sentence Transformers, ChromaDB  
**LLM providers:** Gemini or Groq  
**Database:** SQLAlchemy with SQLite by default

## Project Structure

```text
learnpilot-ai/
├── frontend/
│   ├── app/
│   ├── package.json
│   └── next.config.ts
├── backend/
│   ├── app/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── docker-compose.yml
└── README.md
```

## Run Locally (Windows PowerShell)

### 1. Backend

```powershell
cd backend
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

API documentation: http://localhost:8000/docs

### 2. Frontend

Open a second terminal:

```powershell
cd frontend
npm install
Copy-Item .env.local.example .env.local
npm run dev
```

Frontend: http://localhost:3000

## LLM Configuration

Set your provider and API key in `backend/.env`. Example for Groq:

```env
LLM_PROVIDER=groq
LLM_API_KEY=your_groq_api_key
LLM_MODEL=llama-3.3-70b-versatile
LLM_BASE_URL=https://api.groq.com/openai/v1
```

For Gemini, configure the provider, key, and model according to the settings supported by the backend.

Never commit real API keys or secrets.

## Current Scope and Limitations

This repository contains an MVP scaffold. It is intended for local development and experimentation, not production deployment. Review authentication, authorization, file validation, upload limits, persistent vector storage, background processing, database migrations, and operational security before deploying it for real users.

Scanned PDFs that contain images rather than extractable text may require OCR, which is not included in the current implementation. AI-generated educational content should be reviewed for accuracy.

## Roadmap

- Improve retrieval quality with chunking strategies, hybrid search, and reranking.
- Add evaluation for answer faithfulness, retrieval quality, and citation correctness.
- Add accounts, learning history, and spaced-repetition scheduling.
- Add background ingestion jobs and production database configuration.
- Add automated tests and deployment workflows.

## License

No license has been specified yet. All rights are reserved unless a license is added.
