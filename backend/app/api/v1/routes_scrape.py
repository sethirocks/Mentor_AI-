from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/scrape", tags=["scrape"])


class ScrapeRequest(BaseModel):
    url: str


@router.post("")
def scrape(request: ScrapeRequest):
    return {
        "status": "success",
        "message": f"Mock scrape of: {request.url}",
    }
