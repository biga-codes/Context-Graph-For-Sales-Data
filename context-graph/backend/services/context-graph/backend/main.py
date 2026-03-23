from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import graph, chat, query
from services.db import init_db

app = FastAPI(title="Context Graph API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    init_db()

app.include_router(graph.router, prefix="/api/graph", tags=["graph"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(query.router, prefix="/api/query", tags=["query"])

@app.get("/health")
def health():
    return {"status": "ok"}
