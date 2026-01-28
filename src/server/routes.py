"""API routes for the reading backlog server."""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException

from ..models import Article, ArticleCreate, ArticleUpdate, Priority, Status
from ..services import scrape_article, storage

router = APIRouter(prefix="/api")


@router.post("/articles", response_model=Article)
async def create_article(article_data: ArticleCreate) -> Article:
    """
    Add a new article to the backlog.

    Scrapes metadata from the URL and stores the article.
    """
    try:
        article = await scrape_article(article_data)
        storage.add(article)
        return article
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to scrape article: {str(e)}")


@router.get("/articles", response_model=List[Article])
async def list_articles(
    status: Optional[Status] = None,
    priority: Optional[Priority] = None,
    tag: Optional[str] = None,
    source: Optional[str] = None,
) -> List[Article]:
    """
    List all articles with optional filters.

    - **status**: Filter by read/unread status
    - **priority**: Filter by priority level
    - **tag**: Filter by tag (case-insensitive)
    - **source**: Filter by source domain (partial match)
    """
    return storage.get_all(
        status=status,
        priority=priority,
        tag=tag,
        source=source,
    )


@router.get("/articles/{article_id}", response_model=Article)
async def get_article(article_id: str) -> Article:
    """Get a single article by ID."""
    article = storage.get_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.patch("/articles/{article_id}", response_model=Article)
async def update_article(article_id: str, update: ArticleUpdate) -> Article:
    """
    Update an article's metadata.

    Can update: title, summary, tags, priority, status
    """
    article = storage.update(article_id, update)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.delete("/articles/{article_id}")
async def delete_article(article_id: str) -> dict:
    """Delete an article from the backlog."""
    if storage.delete(article_id):
        return {"status": "deleted", "id": article_id}
    raise HTTPException(status_code=404, detail="Article not found")


@router.post("/articles/{article_id}/read", response_model=Article)
async def mark_as_read(article_id: str) -> Article:
    """Mark an article as read."""
    article = storage.update(article_id, ArticleUpdate(status=Status.READ))
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@router.post("/articles/{article_id}/unread", response_model=Article)
async def mark_as_unread(article_id: str) -> Article:
    """Mark an article as unread."""
    article = storage.update(article_id, ArticleUpdate(status=Status.UNREAD))
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article
