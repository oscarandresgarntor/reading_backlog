"""Web scraper service for extracting article metadata."""

import io
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, unquote

import httpx
import fitz  # pymupdf
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


def clean_text(text: Optional[str]) -> str:
    """Clean and normalize extracted text."""
    if not text:
        return ""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def is_pdf_url(url: str, content_type: Optional[str] = None) -> bool:
    """Check if URL points to a PDF file."""
    # Check by extension
    parsed = urlparse(url)
    path = parsed.path.lower()
    if path.endswith('.pdf'):
        return True

    # Check by content-type header
    if content_type and 'application/pdf' in content_type.lower():
        return True

    return False


def extract_filename_from_url(url: str) -> str:
    """Extract filename from URL path."""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    filename = Path(path).stem  # Get filename without extension
    # Clean up the filename
    filename = filename.replace('_', ' ').replace('-', ' ')
    return filename


def extract_pdf_metadata(pdf_bytes: bytes, url: str) -> dict:
    """Extract metadata and text from PDF bytes using pymupdf."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    # Get PDF metadata
    metadata = doc.metadata

    # Extract title (with fallbacks)
    title = ""
    if metadata.get("title"):
        title = clean_text(metadata["title"])

    # If no title in metadata, try first heading or filename
    if not title:
        # Try to get title from first page text (often the title is at the top)
        if doc.page_count > 0:
            first_page = doc[0]
            blocks = first_page.get_text("blocks")
            if blocks:
                # Get the first non-empty text block (often the title)
                for block in blocks[:3]:  # Check first 3 blocks
                    if block[4]:  # block[4] is the text content
                        potential_title = clean_text(block[4])
                        if len(potential_title) > 5 and len(potential_title) < 200:
                            title = potential_title
                            break

    # Fallback to filename
    if not title:
        title = extract_filename_from_url(url)
    if not title:
        title = f"PDF from {extract_domain(url)}"

    # Extract text for summary (first few pages)
    full_text = ""
    for page_num in range(min(3, doc.page_count)):  # First 3 pages max
        page = doc[page_num]
        full_text += page.get_text()

    summary = clean_text(full_text)[:200]
    if len(full_text) > 200:
        summary += "..."

    # Get dates
    date_published = None
    if metadata.get("creationDate"):
        # PDF dates are in format: D:YYYYMMDDHHmmSS
        date_str = metadata["creationDate"]
        if date_str.startswith("D:"):
            date_str = date_str[2:]
        if len(date_str) >= 8:
            date_published = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"

    doc.close()

    return {
        "title": title,
        "summary": summary,
        "date_published": date_published,
        "author": metadata.get("author"),
    }


async def scrape_pdf(url: str, pdf_bytes: bytes, article_data: ArticleCreate) -> Article:
    """Extract metadata from a PDF and create an Article."""
    pdf_meta = extract_pdf_metadata(pdf_bytes, url)

    return Article(
        url=url,
        title=pdf_meta["title"],
        summary=pdf_meta["summary"],
        source=extract_domain(url),
        date_published=pdf_meta["date_published"],
        tags=article_data.tags,
        priority=article_data.priority,
    )


async def scrape_html(url: str, html: str, article_data: ArticleCreate) -> Article:
    """Extract metadata from HTML and create an Article."""
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

    return Article(
        url=url,
        title=title,
        summary=summary,
        source=extract_domain(url),
        date_published=date_published,
        tags=article_data.tags,
        priority=article_data.priority,
    )


async def scrape_article(article_data: ArticleCreate) -> Article:
    """
    Scrape metadata from a URL and create an Article.

    Supports both HTML pages and PDF files.
    """
    url = str(article_data.url)

    # Fetch the content
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=30.0,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")

        # Check if it's a PDF
        if is_pdf_url(url, content_type):
            return await scrape_pdf(url, response.content, article_data)
        else:
            return await scrape_html(url, response.text, article_data)


def scrape_article_sync(article_data: ArticleCreate) -> Article:
    """Synchronous version of scrape_article for CLI use."""
    import asyncio
    return asyncio.run(scrape_article(article_data))
