from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Represents the information we expect from a chat prompt."""

    message: str


@router.post("")
def chat(request: ChatRequest):
    """Return a friendly placeholder response so the front end can be wired up."""

    return {
        "response": f"Mock reply to: {request.message}",
        "source": "mock",
    }
