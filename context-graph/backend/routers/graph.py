from fastapi import APIRouter, HTTPException
from services.graph_builder import get_full_graph_cached, get_node_neighbors

router = APIRouter()

@router.get("/")
def get_full_graph():
    """Return all nodes and edges."""
    return get_full_graph_cached()

@router.get("/neighbors/{node_id:path}")
def get_neighbors(node_id: str):
    """Return first-degree neighbors of a given node."""
    result = get_node_neighbors(node_id)
    if not result["nodes"]:
        raise HTTPException(status_code=404, detail=f"Node {node_id!r} not found.")
    return result
