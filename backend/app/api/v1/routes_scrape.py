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

DEFAULT_SCRAPE_URL = "https://h-da.de/studium/orientierungssemester"


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


class SubpageContent(BaseModel):
    page: ScrapedPage
    headings: List[str] = Field(default_factory=list)
    paragraphs: List[str] = Field(default_factory=list)


class ScrapeResponse(BaseModel):
    page: ScrapedPage
    text_blocks: List[str]
    links: List[ScrapedLink]
    subpages: List[ScrapedLink] = Field(
        default_factory=list,
        description="Subset of links that stay within the scraped page hierarchy.",
    )
    subpage_details: List[SubpageContent] = Field(
        default_factory=list,
        description="Parsed content for each discovered subpage.",
    )


def _extract_text_blocks(soup: BeautifulSoup) -> List[str]:
    text_blocks: List[str] = []
    for element in soup.find_all(["p", "li", "h2", "h3", "h4"]):
        text = element.get_text(" ", strip=True)
        if text:
            text_blocks.append(text)
    return text_blocks


def _extract_paragraphs(soup: BeautifulSoup) -> List[str]:
    paragraphs: List[str] = []
    for element in soup.find_all("p"):
        text = element.get_text(" ", strip=True)
        if text:
            paragraphs.append(text)
    return paragraphs


def _extract_headings(soup: BeautifulSoup) -> List[str]:
    headings: List[str] = []
    for tag_name in ["h1", "h2", "h3", "h4"]:
        for tag in soup.find_all(tag_name):
            text = tag.get_text(" ", strip=True)
            if text:
                headings.append(text)
    return headings


def _infer_tags(url: str) -> List[str]:
    parsed = urlparse(url)
    segments = [segment for segment in parsed.path.split("/") if segment]
    focus_segments = segments[:2] if len(segments) >= 2 else segments

    tags: List[str] = []
    for segment in focus_segments:
        words = [word.capitalize() for word in segment.replace("-", " ").split()]
        label = " ".join(words)
        if label and label not in tags:
            tags.append(label)
    return tags


def _build_scraped_page(url: str, html: str, soup: BeautifulSoup) -> ScrapedPage:
    metadata = {}

    if soup.title and soup.title.string:
        metadata["title"] = soup.title.string.strip()

    primary_heading_tag = soup.find("h1")
    if primary_heading_tag:
        primary_heading = primary_heading_tag.get_text(" ", strip=True)
        if primary_heading:
            metadata["primary_heading"] = primary_heading

    headings = _extract_headings(soup)
    if headings:
        metadata["headings"] = headings

    paragraphs = _extract_paragraphs(soup)

    parsed_url = urlparse(url)

    return ScrapedPage(
        url=url,
        html=html,
        content="\n\n".join(paragraphs) if paragraphs else None,
        source=parsed_url.netloc or "",
        metadata=metadata,
        tags=_infer_tags(url),
    )


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

    page = _build_scraped_page(target_url, html, soup)
    text_blocks = _extract_text_blocks(soup)
    links = _extract_links(soup, target_url)
    subpages = [link for link in links if link.is_subpage]

    subpage_details: List[SubpageContent] = []

    for link in subpages:
        try:
            subpage_response = await client.get(link.href)
            subpage_response.raise_for_status()
        except httpx.HTTPError:  # pragma: no cover - network variance
            continue

        subpage_html = subpage_response.text
        subpage_soup = BeautifulSoup(subpage_html, "html.parser")
        subpage_page = _build_scraped_page(link.href, subpage_html, subpage_soup)
        subpage_paragraphs = _extract_paragraphs(subpage_soup)
        subpage_headings = _extract_headings(subpage_soup)

        subpage_details.append(
            SubpageContent(
                page=subpage_page,
                headings=subpage_headings,
                paragraphs=subpage_paragraphs,
            )
        )

    return ScrapeResponse(
        page=page,
        text_blocks=text_blocks,
        links=links,
        subpages=subpages,
        subpage_details=subpage_details,
    )
