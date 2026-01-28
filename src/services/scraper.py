"""Web scraper service for extracting article metadata."""

import re
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse, unquote

import httpx
import fitz  # pymupdf
import trafilatura
from trafilatura.settings import use_config

from ..models import Article, ArticleCreate
from .llm import extract_with_llm, is_ollama_running


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


def extract_pdf_text(pdf_bytes: bytes, max_pages: int = 5) -> str:
    """Extract text from PDF for LLM processing."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = ""
    for page_num in range(min(max_pages, doc.page_count)):
        page = doc[page_num]
        full_text += page.get_text()
    doc.close()
    return full_text


def extract_pdf_metadata(pdf_bytes: bytes, url: str, use_llm: bool = True) -> dict:
    """Extract metadata and text from PDF bytes using pymupdf and optionally LLM."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    # Get PDF metadata
    metadata = doc.metadata

    # Extract full text for LLM
    full_text = ""
    for page_num in range(min(5, doc.page_count)):  # First 5 pages
        page = doc[page_num]
        full_text += page.get_text()

    doc.close()

    # Try LLM extraction first
    if use_llm and is_ollama_running():
        llm_result = extract_with_llm(full_text)
        if llm_result:
            return {
                "title": llm_result.get("title", ""),
                "summary": llm_result.get("summary", ""),
                "suggested_tags": llm_result.get("suggested_tags", []),
                "date_published": extract_pdf_date(metadata),
                "author": metadata.get("author"),
                "used_llm": True,
            }

    # Fallback to basic extraction
    title = ""
    if metadata.get("title"):
        title = clean_text(metadata["title"])

    # If no title in metadata, try first heading or filename
    if not title:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.page_count > 0:
            first_page = doc[0]
            blocks = first_page.get_text("blocks")
            if blocks:
                for block in blocks[:3]:
                    if block[4]:
                        potential_title = clean_text(block[4])
                        if len(potential_title) > 5 and len(potential_title) < 200:
                            title = potential_title
                            break
        doc.close()

    # Fallback to filename
    if not title:
        title = extract_filename_from_url(url)
    if not title:
        title = f"PDF from {extract_domain(url)}"

    # Basic summary
    summary = clean_text(full_text)[:200]
    if len(full_text) > 200:
        summary += "..."

    return {
        "title": title,
        "summary": summary,
        "suggested_tags": [],
        "date_published": extract_pdf_date(metadata),
        "author": metadata.get("author"),
        "used_llm": False,
    }


def extract_pdf_date(metadata: dict) -> Optional[str]:
    """Extract date from PDF metadata."""
    if metadata.get("creationDate"):
        date_str = metadata["creationDate"]
        if date_str.startswith("D:"):
            date_str = date_str[2:]
        if len(date_str) >= 8:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return None


def merge_tags(user_tags: List[str], suggested_tags: List[str]) -> List[str]:
    """Merge user-provided tags with LLM-suggested tags."""
    # User tags take priority, add suggested tags that aren't duplicates
    all_tags = list(user_tags)
    user_tags_lower = [t.lower() for t in user_tags]
    for tag in suggested_tags:
        if tag.lower() not in user_tags_lower:
            all_tags.append(tag)
    return all_tags[:6]  # Limit to 6 tags


async def scrape_pdf(url: str, pdf_bytes: bytes, article_data: ArticleCreate) -> Article:
    """Extract metadata from a PDF and create an Article."""
    pdf_meta = extract_pdf_metadata(pdf_bytes, url, use_llm=True)

    # Merge user tags with suggested tags
    tags = merge_tags(article_data.tags, pdf_meta.get("suggested_tags", []))

    return Article(
        url=url,
        title=pdf_meta["title"],
        summary=pdf_meta["summary"],
        source=extract_domain(url),
        date_published=pdf_meta["date_published"],
        tags=tags,
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

    # Get basic metadata
    metadata = trafilatura.extract_metadata(html)

    # Try LLM extraction first
    suggested_tags = []
    if extracted and is_ollama_running():
        llm_result = extract_with_llm(extracted)
        if llm_result:
            title = llm_result.get("title", "")
            summary = llm_result.get("summary", "")
            suggested_tags = llm_result.get("suggested_tags", [])

            # Get date from trafilatura metadata
            date_published = None
            if metadata and metadata.date:
                date_published = metadata.date

            tags = merge_tags(article_data.tags, suggested_tags)

            return Article(
                url=url,
                title=title,
                summary=summary,
                source=extract_domain(url),
                date_published=date_published,
                tags=tags,
                priority=article_data.priority,
            )

    # Fallback to basic extraction
    title = ""
    if metadata and metadata.title:
        title = clean_text(metadata.title)
    if not title:
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', html, re.IGNORECASE)
        if title_match:
            title = clean_text(title_match.group(1))
    if not title:
        title = f"Article from {extract_domain(url)}"

    summary = ""
    if extracted:
        summary = clean_text(extracted)[:200]
        if len(extracted) > 200:
            summary += "..."

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
    Uses LLM (Ollama) for better extraction when available.
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
