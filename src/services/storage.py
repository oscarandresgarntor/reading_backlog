"""JSON file storage service for articles."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..config import ARTICLES_FILE
from ..models import Article, ArticleUpdate, Priority, Status


class StorageService:
    """Handles reading and writing articles to JSON file."""

    def __init__(self, file_path: Path = ARTICLES_FILE):
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Create storage file if it doesn't exist."""
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.file_path.write_text("[]")

    def _load_articles(self) -> List[Dict]:
        """Load raw article data from JSON file."""
        try:
            return json.loads(self.file_path.read_text())
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_articles(self, articles: List[Dict]) -> None:
        """Save article data to JSON file."""
        self.file_path.write_text(
            json.dumps(articles, indent=2, default=str)
        )

    def get_all(
        self,
        status: Optional[Status] = None,
        priority: Optional[Priority] = None,
        tag: Optional[str] = None,
        source: Optional[str] = None,
    ) -> List[Article]:
        """Get all articles with optional filters."""
        articles = [Article(**data) for data in self._load_articles()]

        if status:
            articles = [a for a in articles if a.status == status]
        if priority:
            articles = [a for a in articles if a.priority == priority]
        if tag:
            articles = [a for a in articles if tag.lower() in [t.lower() for t in a.tags]]
        if source:
            articles = [a for a in articles if source.lower() in a.source.lower()]

        # Sort by date_added descending (newest first)
        return sorted(articles, key=lambda a: a.date_added, reverse=True)

    def get_by_id(self, article_id: str) -> Optional[Article]:
        """Get a single article by ID."""
        for data in self._load_articles():
            if data.get("id") == article_id:
                return Article(**data)
        return None

    def add(self, article: Article) -> Article:
        """Add a new article."""
        articles = self._load_articles()
        articles.append(article.model_dump())
        self._save_articles(articles)
        return article

    def update(self, article_id: str, update: ArticleUpdate) -> Optional[Article]:
        """Update an existing article."""
        articles = self._load_articles()

        for i, data in enumerate(articles):
            if data.get("id") == article_id:
                update_data = update.model_dump(exclude_unset=True)
                data.update(update_data)
                articles[i] = data
                self._save_articles(articles)
                return Article(**data)

        return None

    def delete(self, article_id: str) -> bool:
        """Delete an article by ID."""
        articles = self._load_articles()
        original_len = len(articles)
        articles = [a for a in articles if a.get("id") != article_id]

        if len(articles) < original_len:
            self._save_articles(articles)
            return True
        return False

    def export_markdown(self, output_path: Optional[Path] = None) -> str:
        """Export articles to Markdown format."""
        articles = self.get_all()
        output_path = output_path or self.file_path.parent / "reading_backlog.md"

        lines = [
            "# Reading Backlog",
            "",
            f"*Exported: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
            "",
        ]

        # Group by status
        unread = [a for a in articles if a.status == Status.UNREAD]
        read = [a for a in articles if a.status == Status.READ]

        if unread:
            lines.append("## Unread")
            lines.append("")
            for article in unread:
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[article.priority.value]
                tags = f" `{'` `'.join(article.tags)}`" if article.tags else ""
                lines.append(f"- [{article.title}]({article.url}) {priority_emoji}{tags}")
                if article.summary:
                    lines.append(f"  > {article.summary[:100]}...")
            lines.append("")

        if read:
            lines.append("## Read")
            lines.append("")
            for article in read:
                lines.append(f"- [{article.title}]({article.url})")
            lines.append("")

        content = "\n".join(lines)
        output_path.write_text(content)
        return str(output_path)


# Global storage instance
storage = StorageService()
