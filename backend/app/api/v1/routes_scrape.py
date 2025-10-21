"""Routes for scraping external content."""

from __future__ import annotations

from typing import List
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.models import ScrapedPage

router = APIRouter(prefix="/scrape", tags=["scrape"])

DEFAULT_SCRAPE_URL = "https://www.h-da.de/studium/studienangebot"


class ScrapeRequest(BaseModel):
    url: str | None = Field(
        default=None,
        description="Target URL to scrape. Defaults to a representative h-da.de page.",
    )


class ScrapedLink(BaseModel):
    href: str
    text: str | None = None
    is_internal: bool = Field(
        default=False, description="True when the link stays on the origin host."
    )
    is_subpage: bool = Field(
        default=False,
        description=(
            "True when the link points to a subpage under the origin path hierarchy."
        ),
    )


class ScrapeResponse(BaseModel):
    page: ScrapedPage
    text_blocks: List[str]
    links: List[ScrapedLink]
    subpages: List[ScrapedLink] = Field(
        default_factory=list,
        description="Subset of links that stay within the scraped page hierarchy.",
    )


def _extract_text_blocks(soup: BeautifulSoup) -> List[str]:
    text_blocks: List[str] = []
    for element in soup.find_all(["p", "li", "h2", "h3", "h4"]):
        text = element.get_text(" ", strip=True)
        if text:
            text_blocks.append(text)
    return text_blocks


def _extract_links(soup: BeautifulSoup, base_url: str) -> List[ScrapedLink]:
    links: List[ScrapedLink] = []

    parsed_base = urlparse(base_url)
    base_path = parsed_base.path or "/"
    base_dir = base_path if base_path.endswith("/") else f"{base_path}/"

    seen: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href_raw = anchor["href"].strip()
        href = urljoin(base_url, href_raw)

        parsed = urlparse(href)
        if parsed.scheme not in {"http", "https"}:
            continue

        if href in seen:
            continue
        seen.add(href)

        text = anchor.get_text(" ", strip=True) or None

        is_internal = parsed.netloc == parsed_base.netloc
        candidate_path = parsed.path or "/"

        if parsed_base.path in {"", "/"}:
            is_subpage = is_internal and candidate_path not in {"", "/"}
        else:
            is_subpage = is_internal and candidate_path.startswith(base_dir)

        links.append(
            ScrapedLink(
                href=href,
                text=text,
                is_internal=is_internal,
                is_subpage=is_subpage,
            )
        )

    return links


@router.post("", response_model=ScrapeResponse)
async def scrape(request: ScrapeRequest) -> ScrapeResponse:
    """Fetch the HTML of a page and return extracted text and links."""

    target_url = request.url or DEFAULT_SCRAPE_URL

    if not target_url.startswith("http"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scraper only supports http(s) URLs.",
        )

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.get(target_url)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:  # pragma: no cover - network errors hard to trigger in CI
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"Failed to retrieve page: {exc.response.text[:200]}",
        ) from exc
    except httpx.RequestError as exc:  # pragma: no cover - network errors hard to trigger in CI
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not fetch URL '{target_url}': {exc}",
        ) from exc

    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    text_blocks = _extract_text_blocks(soup)
    links = _extract_links(soup, target_url)
    subpages = [link for link in links if link.is_subpage]

    metadata = {}
    if soup.title and soup.title.string:
        metadata["title"] = soup.title.string.strip()

    scraped_page = ScrapedPage(
        url=target_url,
        html=html,
        content="\n\n".join(text_blocks) if text_blocks else None,
        source="scraper",
        metadata=metadata,
    )

    return ScrapeResponse(
        page=scraped_page,
        text_blocks=text_blocks,
        links=links,
        subpages=subpages,
    )
