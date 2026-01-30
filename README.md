# Financial Data Chatbot

A natural language query interface for financial portfolio analysis using AI-powered SQL generation.

## Tech Stack
- **Python 3.13** - Core language
- **DuckDB** - In-memory SQL database for fast analytics
- **OpenAI GPT-4o-mini** - LLM for query understanding and SQL generation
- **Pandas** - Data manipulation
- **ipywidgets** - Interactive Jupyter interface

## Problem Solved
Financial analysts spend significant time writing complex SQL queries to extract insights from trades and holdings data. Non-technical stakeholders struggle to access portfolio metrics like YTD performance, trade counts, and holdings analysis without technical support.

## Solution
This chatbot converts natural language questions into SQL queries automatically. Users ask questions like "Which fund has the best YTD performance?" and receive instant, plain-English answers with accurate data.

**How it works:**
1. LLM analyzes the question and selects appropriate data sources (trades/holdings tables)
2. Generates DuckDB-compatible SQL with schema-aware prompting
3. Executes query against in-memory database
4. Transforms results into business-friendly explanations

The system handles case-insensitive matching, fund name variations, and complex aggregations across 649 trades and 1,022 holdings records, democratizing access to financial insights.