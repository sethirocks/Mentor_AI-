from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.mongo import db
from app.models import Insight

router = APIRouter(prefix="/insights", tags=["insights"])


class InsightsRequest(BaseModel):
    topic: str
    content: str | None = None
    source: str | None = None
    tags: List[str] = Field(default_factory=list)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_insight(request: InsightsRequest) -> Dict[str, Any]:
    """Persist a new insight for the provided topic."""

    content = request.content or f"Auto-generated for {request.topic}"
    insight = Insight(
        topic=request.topic,
        content=content,
        source=request.source,
        tags=request.tags,
    )
    insert_result = db["insights"].insert_one(insight.to_mongo())

    if not insert_result.acknowledged:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store insight",
        )

    persisted = db["insights"].find_one({"_id": insert_result.inserted_id})
    saved_insight = Insight.from_mongo(persisted)
    return {
        "topic": saved_insight.topic,
        "insights": [saved_insight.content],
        "id": saved_insight.id,
    }


@router.get("/{topic}", response_model=List[Insight])
def list_insights(topic: str) -> List[Insight]:
    """Retrieve all insights for a given topic."""

    documents = db["insights"].find({"topic": topic})
    insights: List[Insight] = [Insight.from_mongo(doc) for doc in documents]
    if not insights:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No insights found for topic '{topic}'",
        )
    return insights
