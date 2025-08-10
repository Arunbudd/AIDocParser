# AIDocParser

AIDocParser is an AI-powered backend system for document ingestion, summarization, and semantic search.

## Features
- Upload PDF documents through FastAPI endpoints
- Store documents and chunks in SQLite (default) or PostgreSQL
- Generate document summaries using OpenAI API
- Perform semantic search and Q&A on document content

## Tech Stack
- FastAPI for backend API
- SQLAlchemy for ORM
- SQLite for demo / PostgreSQL for production
- OpenAI API for embeddings and summarization
- FAISS / pgvector for vector search

## Setup Instructions

```bash
# 1. Clone the repository
git clone this repo url
cd AIDocParser

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate    # macOS / Linux
# venv\Scripts\activate     # Windows
```

# 3. Install dependencies
```pip install -r requirements.txt```

# 4. Ensure your OpenAI key is set in app/config.py
  ```
  #Example inside config.py:
  OPENAI_API_KEY = "sk-proj-..."
  ```

# 5. Run the FastAPI server
```uvicorn app.main:app --reload --port 8010```

## Usage

Once the FastAPI server is running, visit:

**[http://127.0.0.1:8010/docs](http://127.0.0.1:8010/docs)**

This will open the **Swagger UI**, where you can test all endpoints.

### API Endpoints
- `POST /upload` – Upload a PDF document
- `POST /ask` – Ask a question about a document
- `GET /documents` – List all documents
- `DELETE /documents/{id}` – Delete a document

## Note on Database Setup

To make setup easier and avoid complex PostgreSQL configuration, I decided to default this project to use **Python's built-in SQLite**. 

After some brainstorming, I realized SQLite works great for demo purposes and lightweight usage. It runs out-of-the-box with no extra dependencies — just clone and go.

You can still switch to PostgreSQL later by updating `USE_SQLITE_FOR_DEMO = False` in `app/db.py` and setting your `DATABASE_URL` accordingly.

