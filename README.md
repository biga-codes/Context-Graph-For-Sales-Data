# Context Graph Explorer
---
A graph-based data exploration system with a natural language query interface. Business entities (orders, deliveries, invoices, payments) are modelled as a graph, visualised with React Flow, and queryable through an LLM-powered chat interface (Gemini or Groq).

---

## Table of Contents

- [Demo](#demo)
- [Architecture](#architecture)
- [Design Decisions](#design-decisions-i-made)
- [Database Choice](#database-choice)
- [Graph Modelling](#graph-modelling)
- [LLM Prompting Strategy](#llm-prompting-strategy)
- [Guardrails](#guardrails)
- [Setup](#setup)
- [Example Queries](#example-queries)
- [Project Structure](#project-structure)
- [Live Deployment Link](#live-deployment-link)
## Demo
I've made a few UI changes as you can see from the first video, the second video details the design decisions/thoughts. Click here to see the entire new UI demo : [click here](https://youtu.be/BZ1vtfX5aSc?si=8V4BYJVI1GWURjjs)


https://github.com/user-attachments/assets/6b0d1a9f-f91b-423b-990e-30237c1d3f3c

https://github.com/user-attachments/assets/d21b0e70-8d17-4d4c-af1d-c02cc57555f5



### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     React (Vite)                        │
│  ┌──────────────────────┐  ┌───────────────────────┐   │
│  │   GraphCanvas        │  │     ChatPanel         │   │
│  │   (React Flow)       │  │   (NL Query UI)       │   │
│  │   EntityNode         │  │   SQL disclosure      │   │
│  │   NodeDetailPanel    │  │   Node highlighting   │   │
│  └──────────────────────┘  └───────────────────────┘   │
│              Zustand global store                        │
└────────────────────────┬────────────────────────────────┘
                         │ REST /api/*
┌────────────────────────▼────────────────────────────────┐
│                  FastAPI (Python)                        │
│  /api/graph/           → graph_builder.py               │
│  /api/chat/            → llm_service.py                 │
│  /api/query/execute    → db.py (SELECT only)            │
└────────────────────────┬────────────────────────────────┘
                         │
        ┌────────────────┴────────────────┐
        │           SQLite                │
        │  (context_graph.db)             │
        └─────────────────────────────────┘
                         │
              Google Gemini 1.5 Flash
```
### Design Decisions I made:
- caching graph nodes server side so they load faster -> this was especially important because I used a free tier web service ( I added this strategy for graph generation to reduce repeated load on the backend server and it really helps with much faster reloads after the first request.)
- adding a small mini index for all major hubs (nodes with the most connections) for quick access, and neighbourhood highlighting ( upto 2nd degree neighbours have been considered by me for this purpose)
- I kept node meta data attached to each node for easy viewing.
- entity types have specific colors and badges so you can differentiate between them
- I added test coverage for graph nodes
to assert unique node ids, valid endpoints, and no malformed nodes during/ from ingestion

### Database Choice

1. I chose SQLite for local data portability (data would be accessible locally), I prioritized simplicity while validating product behavior since
I wanted to reduce infrastructure complexity early and focus on graph logic, UX, and query behavior first.
2. It is a good fit for this dataset size, the data pipeline works naturally with a file-based DB
I ingest JSONL data and convert it into relational tables. A single SQLite file makes this easy to manage, reset, back up, and move.
3. My workload is mostly read-heavy
my backend reads relational data, builds a graph view, and serves it. SQLite performs well for this kind of local read-focused workload
4. I still kept a migration path open by
using standard SQL patterns, so I can move to PostgreSQL later if I need higher concurrency or production-scale features.
   
The graph is constructed in-memory from relational queries in `graph_builder.py`, which means you get the flexibility of SQL (for the LLM query path) AND a graph representation (for the UI) from the same source of truth. For a production deployment with millions of rows, swap to PostgreSQL (same query layer) or add a Neo4j graph layer on top.

### Graph Modelling

Nodes represent business entities: Customer, Order, OrderItem, Product, Delivery, Invoice, Payment, Address.

Edges capture the real flow of data/ relationships :
- `Customer → Order` (placed)
- `Order → OrderItem` (contains)
- `OrderItem → Product` (references)
- `Order → Delivery` (delivered_via)
- `Delivery → Invoice` (triggers)
- `Order → Invoice` (billed_as)
- `Invoice → Payment` (settled_by)

### LLM Prompting Strategy

The Gemini prompt is structured in two stages:

**Stage 1 — Classification + SQL generation**
A system prompt containing the full schema is sent with every user message. The model is instructed to return a strict JSON object with two paths:
- `{"relevant": false, "message": "..."}` — for off-topic queries
- `{"relevant": true, "sql": "...", "explanation": "..."}` — for valid queries

This separation makes guardrails reliable: the model explicitly labels relevance, so the backend can reject without ever executing a query.

**Stage 2 — Answer synthesis**
The raw query results (capped at 50 rows for context) are sent back to Gemini with the original question. The model is asked to produce a 2–4 sentence data-backed answer without mentioning SQL or database internals.


### Guardrails
- I only allow read queries (no writes)
the advantage here is that the AI cannot change or delete important data.
- I restricted the scope of questions that the AI accepts to only the dataset. This helps guard against prompt injections.
- SQL validation before execution (check table+column existence). I validate table and column names before running SQL queries
  and test  before full execution
- Auto-retry: feed DB error back to LLM once and ask it to fix query
- Data grounding guardrail: response generation happens only after SQL execution; if no rows, system returns explicit no-result message
- The backend's `execute_query()` function enforces `SELECT`-only at the string level & any other statement raises a `ValueError` before execution.
- Query guardrail: backend enforces SELECT-only execution and rejects mutating SQL.
- Domain guardrail: out-of-scope prompts are rejected with a fixed dataset-only message.
- Provider/ops guardrail: LLM failures (quota/model/access) are caught and returned as non-crashing API responses.

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- One API key for either:
    - [Google Gemini](https://ai.google.dev)
    - [Groq](https://console.groq.com) 

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# For Groq (recommended free option)
# LLM_PROVIDER=groq
# GROQ_API_KEY=...
# GROQ_MODEL=llama-3.1-8b-instant

# Or for Gemini
# LLM_PROVIDER=gemini
# GEMINI_API_KEY=...
# GEMINI_MODEL=gemini-1.5-flash-latest
```

### Frontend

```bash
cd frontend
npm install
```

### Dataset Ingestion

1. Place the extracted SAP O2C dataset folder (with subfolders like `sales_order_headers/`, `billing_document_items/`, etc.) anywhere on your machine.
2. Run ingestion with the dataset root path (JSONL-based, no mapping edits needed):

```bash
cd backend
python -m services.ingest --data-dir ../sap-o2c-data
```

Notes:
- The loader truncates each mapped table before importing, so reruns are idempotent.
- Missing folders are skipped safely.

### Running

**Terminal 1 — backend:**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

**Terminal 2 — frontend:**
```bash
cd frontend
npm run dev
```


---

## Example Queries

| Question | What it tests |
|---|---|
| Which products are associated with the highest number of billing documents? | JOIN across order_items, invoices, products |
| trace the data flow of product 3001456 | Multi-table JOIN: suggests a centralized production and storage system for product 3001456 |
| Show sales orders that were delivered but never billed | LEFT JOIN + NULL check |
| Which customers have the most orders? | GROUP BY + ORDER BY |
| What is the total payment amount by method? | Aggregation on payments |

---

## Project Structure

```
context-graph/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── requirements.txt
│   ├── .env.example
│   ├── routers/
│   │   ├── graph.py             # /api/graph/*
│   │   ├── chat.py              # /api/chat/
│   │   └── query.py             # /api/query/execute
│   ├── services/
│   │   ├── db.py                # SQLite connection + execute_query
│   │   ├── ingest.py            # CSV → SQLite loader
│   │   ├── graph_builder.py     # Node/edge construction
│   │   └── llm_service.py       # Gemini NL→SQL pipeline
│   └── data/                    # context_graph.db (gitignored)
│
└── frontend/
    ├── index.html
    ├── vite.config.js
    ├── package.json
    └── src/
        ├── App.jsx
        ├── main.jsx
        ├── styles/global.css
        ├── store/useStore.js    # Zustand state
        ├── services/
        │   ├── api.js           # Axios wrappers
        │   └── layout.js        # Dagre auto-layout
        └── components/
            ├── Navbar.jsx
            ├── GraphCanvas.jsx  # React Flow canvas
            ├── EntityNode.jsx   # Custom RF node
            ├── NodeDetailPanel.jsx
            └── ChatPanel.jsx    # Chat + SQL disclosure
```


# Live Deployment Link:
https://context-graph-for-sales-data-front-end.onrender.com/




