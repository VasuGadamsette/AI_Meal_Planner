from fastapi import APIRouter, Depends, HTTPException

from app.auth import admin_user
from app.rag.service import catalog_status, rebuild

router = APIRouter(prefix="/api/rag", tags=["rag"] )


@router.get("/status")
def status():
    return catalog_status()


@router.post("/rebuild")
def rebuild_index(_=Depends(admin_user)):
    try:
        count = rebuild()
        return {"ok": True, "indexed_recipes": count}
    except Exception as exc:
        raise HTTPException(500, f"RAG index rebuild failed: {exc}")
