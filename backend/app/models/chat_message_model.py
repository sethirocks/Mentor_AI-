"""Pydantic model for storing chat transcripts."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from bson import ObjectId
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Represents a single chat message between a user and the assistant."""

    id: Optional[str] = Field(default=None, alias="_id")
    conversation_id: Optional[str] = None
    role: str
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, str] = Field(default_factory=dict)

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_encoders": {ObjectId: str},
    }

    @classmethod
    def from_mongo(cls, data: dict) -> "ChatMessage":
        if not data:
            raise ValueError("No data provided to instantiate ChatMessage")
        mongo_data = data.copy()
        if "_id" in mongo_data:
            mongo_data["_id"] = str(mongo_data["_id"])
        return cls(**mongo_data)

    def to_mongo(self) -> dict:
        payload = self.model_dump(by_alias=True)
        if payload.get("_id") is None:
            payload.pop("_id", None)
        return payload
