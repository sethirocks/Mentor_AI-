from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/scrape", tags=["scrape"])


class ScrapeRequest(BaseModel):
    """Collect the website address the scraper should eventually visit."""

    url: str


@router.post("")
def scrape(request: ScrapeRequest):
    """Acknowledge the scrape request and indicate it is queued for processing."""

    return {
        "url": request.url,
        "status": "scrape_pending",
    }
