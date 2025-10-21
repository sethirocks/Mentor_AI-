"""Utility functions for crawling and extracting structured content from h-da pages."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

import re
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


DEFAULT_TIMEOUT = 10
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass
class PageContent:
    """Structured representation of a scraped page."""

    url: str
    title: Optional[str]
    headings: List[str] = field(default_factory=list)
    paragraphs: List[str] = field(default_factory=list)
    content: str = ""
    metadata: dict[str, List[str] | str] = field(default_factory=dict)
    source: str = ""
    tags: List[str] = field(default_factory=list)
    retrieved_at: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None

    def to_dict(self) -> dict:
        payload = {
            "url": self.url,
            "title": self.title,
            "headings": self.headings,
            "paragraphs": self.paragraphs,
            "content": self.content,
            "metadata": self.metadata,
            "source": self.source,
            "tags": self.tags,
            "retrieved_at": self.retrieved_at,
        }
        if self.error:
            payload["error"] = self.error
        return payload


def scrape_section(base_url: str) -> List[PageContent]:
    """Scrape a base URL and all internal sub-pages.

    Args:
        base_url: Entry point for the scraper.

    Returns:
        A list of PageContent objects, one per discovered page.
    """

    normalized_base = normalize_url(base_url)
    html = fetch_html(normalized_base)
    subpages = discover_links(normalized_base, html)

    results: List[PageContent] = []
    for link in subpages:
        try:
            page_html = fetch_html(link)
        except Exception as exc:  # pragma: no cover - network errors are runtime issues
            results.append(
                PageContent(
                    url=link,
                    title=None,
                    error=str(exc),
                    source=urlparse(link).netloc,
                    tags=extract_path_segments(link),
                )
            )
            continue

        soup = BeautifulSoup(page_html, "html.parser")
        page = parse_page(link, soup)
        results.append(page)

    return results


def fetch_html(url: str) -> str:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.text


def normalize_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme:
        parsed = parsed._replace(scheme="https")
    if not parsed.netloc:
        raise ValueError("URL must include a domain")
    cleaned = parsed._replace(fragment="", query="")
    return urlunparse(cleaned)


def discover_links(base_url: str, html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    base_parsed = urlparse(base_url)
    allowed_prefix = base_parsed.path.rstrip("/") or "/"

    discovered = {base_url}
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()
        if not href or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        candidate = urljoin(base_url, href)
        candidate = normalize_url(candidate)
        parsed = urlparse(candidate)
        if parsed.netloc != base_parsed.netloc:
            continue
        if not parsed.path.startswith(allowed_prefix):
            continue
        if candidate not in discovered:
            discovered.add(candidate)

    return sorted(discovered)


def parse_page(url: str, soup: BeautifulSoup) -> PageContent:
    title = extract_title(soup)
    headings = extract_headings(soup)
    paragraphs = extract_paragraphs(soup)
    breadcrumbs = extract_breadcrumbs(soup)
    source = urlparse(url).netloc
    tags = extract_path_segments(url)

    metadata = {}
    if breadcrumbs:
        metadata["breadcrumbs"] = breadcrumbs
    if headings:
        metadata["heading_count"] = str(len(headings))

    content = "\n\n".join(paragraphs)
    return PageContent(
        url=url,
        title=title,
        headings=headings,
        paragraphs=paragraphs,
        content=content,
        metadata=metadata,
        source=source,
        tags=tags,
    )


def extract_title(soup: BeautifulSoup) -> Optional[str]:
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return og_title["content"].strip()

    if soup.title and soup.title.string:
        return soup.title.string.strip()

    first_heading = soup.find("h1")
    if first_heading:
        return first_heading.get_text(strip=True)

    return None


def extract_headings(soup: BeautifulSoup) -> List[str]:
    headings: List[str] = []
    for tag in soup.find_all(re.compile(r"^h[1-3]$")):
        text = tag.get_text(separator=" ", strip=True)
        if text:
            headings.append(text)
    return headings


def extract_paragraphs(soup: BeautifulSoup) -> List[str]:
    paragraphs: List[str] = []
    for paragraph in soup.find_all("p"):
        text = normalize_whitespace(paragraph.get_text(" ", strip=True))
        if text:
            paragraphs.append(text)
    return paragraphs


def extract_breadcrumbs(soup: BeautifulSoup) -> List[str]:
    breadcrumb_container = soup.select_one('[class*="breadcrumb"]')
    if not breadcrumb_container:
        return []

    items: List[str] = []
    for element in breadcrumb_container.find_all(["li", "span", "a"]):
        text = element.get_text(strip=True)
        if text:
            items.append(text)
    return items


def extract_path_segments(url: str) -> List[str]:
    path = urlparse(url).path
    segments = [segment for segment in path.split("/") if segment]
    return segments


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()