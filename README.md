# AI Support Ticket Triage Assistant

A learning prototype that classifies support tickets, retrieves grounded FAQ content, drafts a response, validates it, and routes sensitive or uncertain cases to a human agent.

## Architecture

```text
Streamlit -> FastAPI -> PostgreSQL
                    |
                    +-> LangChain classifier
                    +-> ChromaDB FAQ retriever
                    +-> LangChain RAG draft generator
                    +-> Validation + escalation policy
                    +-> automatic answer OR human review queue
```

The application defaults to deterministic mock AI so that the complete workflow can be demonstrated without an API key. Set `USE_MOCK_AI=false` and `OPENAI_API_KEY` to use OpenAI through LangChain.

## Run locally

```powershell
cd support-ticket-triage
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m ingestion.seed_faqs
uvicorn app.main:app --reload
```

In a second terminal:

```powershell
streamlit run streamlit_app.py
```

Open `http://localhost:8501`. The API documentation is at `http://localhost:8000/docs`.

## Run with PostgreSQL

```powershell
docker compose up --build
```

The API is available at `http://localhost:8000` and Streamlit at `http://localhost:8501`.

## Demo workflow

1. Submit a normal password-reset ticket. It should become `answered` automatically.
2. Submit a refund or duplicate-payment ticket. It should become `waiting_for_review`.
3. Open the Agent Review page, approve or edit the draft, and submit the review.
4. Query the ticket status to see the complete audit history.

The Streamlit form accepts optional text attachment metadata in this prototype. File content is intentionally not sent to the model yet; add a scanned document pipeline before enabling arbitrary uploads in production.

## Tests

```powershell
pytest -q
```
