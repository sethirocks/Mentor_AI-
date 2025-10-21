"""Pydantic model that captures raw and parsed data from scraped pages."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Union

from bson import ObjectId
from pydantic import BaseModel, Field, HttpUrl


class ScrapedPage(BaseModel):
    """Represents the persisted structure for scraped web pages."""

    id: Optional[str] = Field(default=None, alias="_id")
    url: HttpUrl
    title: Optional[str] = None
    headings: List[str] = Field(default_factory=list)
    paragraphs: List[str] = Field(default_factory=list)
    content: str = ""
    metadata: Dict[str, Union[List[str], str]] = Field(default_factory=dict)
    source: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }

    # ---------- Mongo helpers ----------

    @classmethod
    def from_mongo(cls, data: dict) -> "ScrapedPage":
        """Convert a MongoDB document into a ScrapedPage instance."""
        if not data:
            raise ValueError("No data provided to instantiate ScrapedPage")
        mongo_data = data.copy()
        if "_id" in mongo_data:
            mongo_data["_id"] = str(mongo_data["_id"])
        return cls(**mongo_data)

    def to_mongo(self) -> dict:
        """Convert the Pydantic model into a MongoDB-safe dictionary."""
        payload = self.model_dump(by_alias=True)

        # remove _id if it's None
        if payload.get("_id") is None:
            payload.pop("_id", None)

        # ✅ force url to be stored as plain string
        if "url" in payload and not isinstance(payload["url"], str):
            payload["url"] = str(payload["url"])

        # ✅ ensure all list/dict fields are serializable
        if "metadata" in payload and isinstance(payload["metadata"], dict):
            payload["metadata"] = {
                str(k): v for k, v in payload["metadata"].items()
            }

        return payload