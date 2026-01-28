"""Web scraper service for extracting article metadata."""

import re
from urllib.parse import urlparse

import httpx
import trafilatura
from trafilatura.settings import use_config

from ..models import Article, ArticleCreate


# Configure trafilatura for better extraction
TRAF_CONFIG = use_config()
TRAF_CONFIG.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")


def extract_domain(url: str) -> str:
    """Extract clean domain name from URL."""
    parsed = urlparse(url)
    domain = parsed.netloc
    # Remove www. prefix
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


from typing import Optional

def clean_text(text: Optional[str]) -> str:
    """Clean and normalize extracted text."""
    if not text:
        return ""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


async def scrape_article(article_data: ArticleCreate) -> Article:
    """
    Scrape metadata from a URL and create an Article.

    Uses trafilatura for main content extraction with httpx fallback
    for basic metadata.
    """
    url = str(article_data.url)

    # Fetch the page
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=30.0,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        html = response.text

    # Extract with trafilatura
    extracted = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
        output_format="txt",
        config=TRAF_CONFIG,
    )

    # Get metadata
    metadata = trafilatura.extract_metadata(html)

    # Build title (with fallbacks)
    title = ""
    if metadata and metadata.title:
        title = clean_text(metadata.title)
    if not title:
        # Try to extract from HTML title tag
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        if title_match:
            title = clean_text(title_match.group(1))
    if not title:
        title = f"Article from {extract_domain(url)}"

    # Build summary (first ~200 chars of content)
    summary = ""
    if extracted:
        summary = clean_text(extracted)[:200]
        if len(extracted) > 200:
            summary += "..."

    # Get publication date if available
    date_published = None
    if metadata and metadata.date:
        date_published = metadata.date

    # Create article
    return Article(
        url=url,
        title=title,
        summary=summary,
        source=extract_domain(url),
        date_published=date_published,
        tags=article_data.tags,
        priority=article_data.priority,
    )


def scrape_article_sync(article_data: ArticleCreate) -> Article:
    """Synchronous version of scrape_article for CLI use."""
    import asyncio
    return asyncio.run(scrape_article(article_data))
