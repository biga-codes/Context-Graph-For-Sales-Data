from pathlib import Path
import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from services.db import init_db, execute_query

logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).parent / ".env")

from routers import graph, chat, query

app = FastAPI(title="Context Graph API", version="1.0.0")

allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()
    
    # Auto-ingest SAP data on first boot if database is empty
    try:
        result = execute_query("SELECT COUNT(*) as cnt FROM sales_order_headers")
        row_count = result[0]["cnt"] if result else 0
        if row_count == 0:
            logger.info("Database is empty, attempting auto-ingestion...")
            from services.ingest import ingest
            # Try common data paths
            data_paths = [
                Path(__file__).parent.parent.parent / "sap-o2c-data",
                Path(__file__).parent.parent / "sap-o2c-data",
                Path("/var/data/sap-o2c-data"),
            ]
            for data_path in data_paths:
                if data_path.exists():
                    logger.info(f"Found data at {data_path}, ingesting...")
                    ingest(str(data_path))
                    logger.info("Auto-ingestion completed successfully")
                    break
            else:
                logger.warning("SAP data directory not found, skipping ingestion")
    except Exception as e:
        logger.warning(f"Auto-ingestion failed (non-fatal): {e}")

app.include_router(graph.router, prefix="/api/graph", tags=["graph"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(query.router, prefix="/api/query", tags=["query"])

@app.get("/health")
def health():
    return {"status": "ok"}
