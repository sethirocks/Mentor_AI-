from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/insights", tags=["insights"])


class InsightsRequest(BaseModel):
    topic: str


@router.post("")
def generate_insights(request: InsightsRequest):
    return {
        "topic": request.topic,
        "insights": [f"Mock insight related to {request.topic}"],
    }
