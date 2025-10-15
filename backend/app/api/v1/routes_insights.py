from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/insights", tags=["insights"])


class InsightsRequest(BaseModel):
    """Describe the question we want the (future) insights engine to answer."""

    query: str


@router.post("")
def create_insight(request: InsightsRequest):
    """Return a sample insight payload while the real logic is under construction."""

    return {
        "insight": f"Mock insight generated for: {request.query}",
        "confidence": 0.0,
    }
