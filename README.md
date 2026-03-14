# Financial Data Chatbot

A production-ready natural language interface for financial portfolio analysis powered by GPT-4o-mini and DuckDB.

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Web framework | FastAPI + Uvicorn |
| Database | DuckDB (in-memory) |
| LLM | OpenAI GPT-4o-mini |
| Data | Pandas |
| Container | Docker / Docker Compose |

## Problem Solved

Financial analysts spend significant time writing complex SQL queries to extract insights from trades and holdings data. Non-technical stakeholders struggle to access portfolio metrics like YTD performance, trade counts, and holdings analysis without technical support.

## Solution

The chatbot converts natural language questions into SQL queries automatically. Users ask questions like *"Which fund has the best YTD performance?"* and receive instant, plain-English answers backed by accurate data.

**Pipeline:**
1. GPT-4o-mini selects the appropriate data source (trades / holdings / both)
2. GPT-4o-mini generates DuckDB-compatible SQL with schema-aware prompting
3. Query is executed against an in-memory DuckDB database
4. Results are translated into a business-friendly explanation

The system handles case-insensitive matching, fund-name variations, and complex aggregations across 649 trade and 1,022 holdings records.

---

## Quick Start

### 1. Local development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set your OpenAI key
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...

# Start the server
uvicorn app:app --reload
```

Open **http://localhost:8000** in your browser.

### 2. Docker Compose (recommended for production)

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...

docker compose up --build
```

The app will be available at **http://localhost:8000**.

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Chat web UI |
| `GET` | `/health` | Health-check (returns `{"status":"ok"}`) |
| `POST` | `/chat` | Ask a question |

### POST /chat

**Request body:**
```json
{ "question": "Which fund has the best YTD performance?" }
```

**Response:**
```json
{
  "answer": "Fund X leads with a YTD profit of $1.2 M …",
  "sql": "SELECT PortfolioName, SUM(PL_YTD) FROM holdings …",
  "sources": ["holdings"],
  "error": null
}
```

---

## Project Structure

```
.
├── app.py              # FastAPI application (routes, models)
├── chatbot.py          # Core pipeline (data loading, LLM, SQL execution)
├── requirements.txt    # Python dependencies
├── Dockerfile          # Multi-stage Docker image
├── docker-compose.yml  # Compose service definition
├── .env.example        # Environment variable template
├── templates/
│   └── index.html      # Chat web UI
├── static/
│   ├── style.css       # UI styles
│   └── script.js       # UI logic
├── trades.csv          # Trade data (649 records)
├── holdings.csv        # Holdings data (1,022 records)
└── financial_chatbot.ipynb  # Original prototype notebook
```