"""
Core chatbot logic for the Financial Data Chatbot.
Handles data loading, LLM-based SQL generation, query execution, and result explanation.
"""

import json
import os
import logging
from typing import Any, Dict, List

import duckdb
import pandas as pd
from openai import OpenAI

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Database setup (module-level singleton)
# ---------------------------------------------------------------------------

conn = duckdb.connect(":memory:")

trades_df = pd.read_csv(os.path.join(os.path.dirname(__file__), "trades.csv"))
conn.register("trades", trades_df)

holdings_df = pd.read_csv(os.path.join(os.path.dirname(__file__), "holdings.csv"))
conn.register("holdings", holdings_df)

trades_funds: List[tuple] = conn.execute(
    "SELECT DISTINCT PortfolioName FROM trades ORDER BY PortfolioName"
).fetchall()

holdings_funds: List[tuple] = conn.execute(
    "SELECT DISTINCT PortfolioName FROM holdings ORDER BY PortfolioName"
).fetchall()

logger.info(
    "Data loaded — %d trade records, %d holdings records",
    len(trades_df),
    len(holdings_df),
)

# ---------------------------------------------------------------------------
# Schema metadata
# ---------------------------------------------------------------------------

SCHEMA_METADATA: Dict[str, Any] = {
    "trades": {
        "description": "Transaction records of buy/sell/cover trades executed in various funds",
        "columns": {
            "id": "Unique trade identifier",
            "RevisionId": "Trade revision number",
            "TradeTypeName": "Type of trade (Buy, Sell, Sell Short, Buy Fixed/Floating Rate, Cover Short, Buy Protection)",
            "SecurityId": "Unique identifier for security/asset",
            "SecurityType": "Type of security (Equity, Bond, etc.)",
            "Name": "Security name/description",
            "Ticker": "Stock/Security ticker symbol",
            "TradeDate": "Date trade was executed",
            "SettleDate": "Date trade settled",
            "Quantity": "Number of shares/units traded",
            "Price": "Price per unit at trade",
            "Principal": "Total transaction value (Quantity × Price)",
            "Interest": "Interest accrued/paid on trade",
            "TotalCash": "Total cash flow for trade",
            "PortfolioName": "Fund/Portfolio name",
            "CustodianName": "Custodian/broker handling the trade",
            "StrategyName": "Investment strategy",
            "Counterparty": "Entity on other side of trade",
            "AllocationRule": "How trade is allocated across sub-portfolios",
        },
        "key_filters": ["PortfolioName", "TradeTypeName", "SecurityType", "Counterparty"],
    },
    "holdings": {
        "description": "Current positions held in each fund as of a specific date",
        "columns": {
            "AsOfDate": "Date for which holdings are reported",
            "PortfolioName": "Fund/Portfolio name",
            "SecurityId": "Unique identifier for security/asset",
            "SecurityTypeName": "Type of security (Bond, Equity, etc.)",
            "SecName": "Security identifier/ISIN",
            "Qty": "Current quantity held",
            "Price": "Current price per unit",
            "FXRate": "Foreign exchange rate for currency conversion",
            "MV_Local": "Market value in local currency (Qty × Price)",
            "MV_Base": "Market value in base currency (MV_Local × FXRate)",
            "PL_DTD": "Profit/Loss Day-To-Date",
            "PL_QTD": "Profit/Loss Quarter-To-Date",
            "PL_MTD": "Profit/Loss Month-To-Date",
            "PL_YTD": "Profit/Loss Year-To-Date (cumulative gain/loss from start of year)",
            "StartQty": "Quantity at start of year",
            "StartPrice": "Price at start of year",
            "StartFXRate": "FX rate at start of year",
        },
        "key_filters": ["PortfolioName", "SecurityTypeName", "AsOfDate"],
    },
}


# ---------------------------------------------------------------------------
# OpenAI client (lazy initialization so the module can be imported without a key)
# ---------------------------------------------------------------------------

def _get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY environment variable is not set.")
    return OpenAI(api_key=api_key)


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def decide_data_source(user_question: str) -> Dict[str, Any]:
    """Ask the LLM which data source(s) are needed to answer the question."""
    client = _get_openai_client()

    prompt = f"""You are a financial data expert. Analyze this question and decide which data source(s) to use.

Question: {user_question}

Available sources:
1. TRADES - Contains buy/sell transaction history
2. HOLDINGS - Contains current positions and P&L data
3. BOTH - If you need information from both tables

You have the following funds in TRADES: {trades_funds}
You have the following funds in HOLDINGS: {holdings_funds}

Always try to match user input with these fund names, handling case sensitivity and typos.

If the question is about trades, trade types, trade dates, quantities, prices, or counterparties → use "trades".
If the question is about holdings, quantities held, market values, or profit/loss → use "holdings".

Respond in JSON format ONLY:
{{
    "sources": ["trades"] or ["holdings"] or ["trades", "holdings"],
    "reasoning": "Brief explanation of why these sources"
}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse decide_data_source response: %s", raw)
        return {"sources": ["trades", "holdings"], "reasoning": "Default to both sources"}


def generate_sql(user_question: str, sources: List[str]) -> Dict[str, Any]:
    """Generate a DuckDB SQL query for the given question using the chosen sources."""
    client = _get_openai_client()

    schema_context = ""
    if "trades" in sources:
        schema_context += f"\nTRADES TABLE:\n{json.dumps(SCHEMA_METADATA['trades'], indent=2)}\n"
    if "holdings" in sources:
        schema_context += f"\nHOLDINGS TABLE:\n{json.dumps(SCHEMA_METADATA['holdings'], indent=2)}\n"

    prompt = f"""You are a SQL expert for financial data. Generate a DuckDB SQL query to answer this question.

{schema_context}

Question: {user_question}

HARD RULES:
1. Use DuckDB SQL syntax only — NO PostgreSQL-specific syntax.
2. NEVER use ILIKE; use LOWER() comparisons instead.
3. NEVER use ARRAY or ANY; use WHERE LOWER(col) = LOWER('value').
4. For top/best funds by profit: SELECT PortfolioName, SUM(PL_YTD) FROM holdings GROUP BY PortfolioName ORDER BY 2 DESC LIMIT 3
5. Profit should always be expressed as positive values; negate if needed.
6. Handle case sensitivity and typos using LOWER().
7. Available funds in trades: {trades_funds}
8. Available funds in holdings: {holdings_funds}
9. Always answer from data; do not fabricate results.
10. Return valid DuckDB SQL only.

Respond in JSON format ONLY:
{{
    "sql": "SELECT ... FROM ...",
    "explanation": "What this query does"
}}"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse generate_sql response: %s", raw)
        return {"sql": "", "explanation": "Failed to generate SQL"}


def execute_query(sql: str) -> Dict[str, Any]:
    """Execute a SQL query against the in-memory DuckDB database."""
    if not sql or not sql.strip():
        return {"success": False, "data": [], "row_count": 0, "error": "Empty SQL query"}

    try:
        result = conn.execute(sql).fetchall()
        description = conn.execute(sql).description
        columns = [desc[0] for desc in description] if description else []
        data = [dict(zip(columns, row)) for row in result]
        return {"success": True, "data": data, "row_count": len(data), "error": None}
    except Exception as exc:
        logger.warning("Query execution error: %s | SQL: %s", exc, sql)
        return {"success": False, "data": [], "row_count": 0, "error": str(exc)}


def explain_results(user_question: str, query_data: Dict[str, Any]) -> str:
    """Translate raw query results into a plain-English business answer."""
    if not query_data["success"]:
        return f"Sorry, I couldn't find the answer. Error: {query_data['error']}"
    if query_data["row_count"] == 0:
        return "Sorry, I could not find any matching data for your question."

    client = _get_openai_client()
    data_str = json.dumps(query_data["data"], indent=2)

    prompt = f"""You are a financial analyst explaining query results to business users.

Original Question: {user_question}

Query Results ({query_data['row_count']} rows):
{data_str}

Instructions:
1. Answer the question directly and concisely.
2. Include specific numbers and fund names from the data.
3. Highlight significant findings.
4. Keep the answer under 150 words.
5. Use business-friendly plain text — no asterisks, bold, italics, or markdown.
6. Do NOT mention SQL queries or technical data structures.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0,
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def financial_chatbot(user_question: str) -> Dict[str, Any]:
    """
    Run the full chatbot pipeline for a user question.

    Returns a dict with:
        answer  (str)  – natural language answer
        sql     (str)  – generated SQL (for transparency)
        sources (list) – data sources used
        error   (str | None)
    """
    logger.info("Processing question: %s", user_question)

    source_decision = decide_data_source(user_question)
    sources = source_decision.get("sources", ["trades", "holdings"])

    sql_gen = generate_sql(user_question, sources)
    sql = sql_gen.get("sql", "")

    if not sql:
        return {
            "answer": "Sorry, I could not generate a query for your question. Please try rephrasing.",
            "sql": "",
            "sources": sources,
            "error": "SQL generation failed",
        }

    exec_result = execute_query(sql)

    answer = explain_results(user_question, exec_result)

    return {
        "answer": answer,
        "sql": sql,
        "sources": sources,
        "error": exec_result.get("error"),
    }
