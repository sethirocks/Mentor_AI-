from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from app.core.scraper import normalize_url, scrape_section

router = APIRouter(prefix="/scrape", tags=["scrape"])


class ScrapeRequest(BaseModel):
    url: HttpUrl = Field(description="Base URL from the h-da website to crawl")


class ScrapedPage(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    headings: List[str] = Field(default_factory=list)
    paragraphs: List[str] = Field(default_factory=list)
    content: str = ""
    metadata: dict = Field(default_factory=dict)
    source: str
    tags: List[str] = Field(default_factory=list)
    retrieved_at: datetime
    error: Optional[str] = None


class ScrapeResponse(BaseModel):
    base_url: HttpUrl
    page_count: int
    pages: List[ScrapedPage]


@router.post("")
def scrape(request: ScrapeRequest) -> ScrapeResponse:
    try:
        normalized = normalize_url(str(request.url))
        pages = scrape_section(normalized)
    except Exception as exc:  # pragma: no cover - runtime validation
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    payload = [ScrapedPage(**page.to_dict()) for page in pages]
    return ScrapeResponse(base_url=normalized, page_count=len(payload), pages=payload)