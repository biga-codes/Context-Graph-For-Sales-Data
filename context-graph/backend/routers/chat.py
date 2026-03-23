from fastapi import APIRouter
from pydantic import BaseModel
from services.llm_service import query_pipeline

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@router.post("/")
def chat(req: ChatRequest):
    """Accept a natural language query and return a grounded answer."""
    result = query_pipeline(req.message.strip())
    return result
