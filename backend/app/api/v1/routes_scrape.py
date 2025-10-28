from datetime import datetime
from typing import Dict, List, Optional, Union
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from app.core.mongo import db
from app.core.scraper import normalize_url, scrape_section
from app.models import ScrapedPage as PersistedScrapedPage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scrape", tags=["scrape"])


class ScrapeRequest(BaseModel):
    url: HttpUrl = Field(description="Base URL from the h-da website to crawl")


class ScrapedPageResponse(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    headings: List[str] = Field(default_factory=list)
    paragraphs: List[str] = Field(default_factory=list)
    content: str = ""
    metadata: Dict[str, Union[List[str], str]] = Field(default_factory=dict)
    source: str
    tags: List[str] = Field(default_factory=list)
    retrieved_at: datetime
    error: Optional[str] = None


class ScrapeResponse(BaseModel):
    base_url: HttpUrl
    page_count: int
    pages: List[ScrapedPageResponse]


@router.post("")
def scrape(request: ScrapeRequest) -> ScrapeResponse:
    try:
        normalized = normalize_url(str(request.url))
        logger.info(f"[Scraper] Base URL to scrape: {normalized}")
        pages = scrape_section(normalized)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    payload: List[ScrapedPageResponse] = []

    for page in pages:
        page_payload = ScrapedPageResponse(**page.to_dict())
        logger.info(f"↪ Scraped subpage: {page_payload.url}")
        payload.append(page_payload)

        if page_payload.error:
            logger.warning(f"[Scraper] Failed to scrape: {page_payload.url} → {page_payload.error}")
            continue

        persisted_page = PersistedScrapedPage(
            url=str(page_payload.url),  # ✅ ensure string type
            title=page_payload.title,
            headings=page_payload.headings,
            paragraphs=page_payload.paragraphs,
            content=page_payload.content,
            metadata=page_payload.metadata,
            source=page_payload.source,
            tags=page_payload.tags,
            retrieved_at=page_payload.retrieved_at,
            error=page_payload.error,
        )

        # ✅ make sure the filter URL is also a string
        db["scraped_pages"].update_one(
            {"url": str(persisted_page.url)},
            {"$set": persisted_page.to_mongo()},
            upsert=True,
        )
        logger.info(f"[Scraper] Saved: {persisted_page.url} to MongoDB")

    return ScrapeResponse(
        base_url=normalized,
        page_count=len(payload),
        pages=payload,
    )