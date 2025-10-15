#health check endpoint
from fastapi import APIRouter, HTTPException
from app.core import mongo  # import the module, not 'db'

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
async def health():
    if mongo.db is None:
        # Startup didn’t connect yet (or failed)
        raise HTTPException(status_code=503, detail="DB not connected")
    pong = await mongo.db.command("ping")
    return {"status": "ok", "mongo": pong.get("ok", 0), "version": "v1"}