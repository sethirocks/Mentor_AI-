"""Pydantic model that captures raw and parsed data from scraped pages."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class ScrapedPage(BaseModel):
    """Represents the persisted structure for scraped web pages."""

    id: Optional[str] = Field(default=None, alias="_id")
    url: str
    html: str
    content: Optional[str] = None
    source: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }

    @classmethod
    def from_mongo(cls, data: dict) -> "ScrapedPage":
        if not data:
            raise ValueError("No data provided to instantiate ScrapedPage")
        mongo_data = data.copy()
        if "_id" in mongo_data:
            mongo_data["_id"] = str(mongo_data["_id"])
        return cls(**mongo_data)

    def to_mongo(self) -> dict:
        payload = self.model_dump(by_alias=True)
        if payload.get("_id") is None:
            payload.pop("_id", None)
        return payload
