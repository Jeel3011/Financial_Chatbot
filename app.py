"""
Financial Data Chatbot — Production FastAPI Application
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Import chatbot logic (loads data at module level)
from chatbot import financial_chatbot  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Financial Chatbot starting up…")
    yield
    logger.info("Financial Chatbot shutting down…")


app = FastAPI(
    title="Financial Data Chatbot",
    description="Natural language interface for financial portfolio analysis",
    version="1.0.0",
    lifespan=lifespan,
)

# Static files and Jinja2 templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000, description="User question")


class ChatResponse(BaseModel):
    answer: str
    sql: str
    sources: list[str]
    error: str | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve the chat UI."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    """Health-check endpoint for load balancers / container orchestrators."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    """Process a natural language question and return a structured response."""
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    result = financial_chatbot(question)
    return ChatResponse(**result)
