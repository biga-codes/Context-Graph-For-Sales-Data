from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.db import execute_query

router = APIRouter()

class QueryRequest(BaseModel):
    sql: str

@router.post("/execute")
def execute(req: QueryRequest):
    """Execute a raw SELECT query (dev/debug endpoint)."""
    try:
        rows = execute_query(req.sql)
        return {"rows": rows, "count": len(rows)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
