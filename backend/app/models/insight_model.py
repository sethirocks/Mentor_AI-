"""Pydantic model representing an insight entry."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class Insight(BaseModel):
    """Represents a generated or user provided insight."""

    id: Optional[str] = Field(default=None, alias="_id")
    topic: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }

    @classmethod
    def from_mongo(cls, data: dict) -> "Insight":
        """Create an :class:`Insight` instance from a MongoDB document."""

        if not data:
            raise ValueError("No data provided to instantiate Insight")
        mongo_data = data.copy()
        if "_id" in mongo_data:
            mongo_data["_id"] = str(mongo_data["_id"])
        return cls(**mongo_data)

    def to_mongo(self) -> dict:
        """Return a MongoDB-friendly representation of the insight."""

        payload = self.model_dump(by_alias=True)
        if payload.get("_id") is None:
            payload.pop("_id", None)
        return payload
