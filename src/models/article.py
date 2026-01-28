"""Article data models using Pydantic."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl


class Priority(str, Enum):
    """Article reading priority."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Status(str, Enum):
    """Article reading status."""
    UNREAD = "unread"
    READ = "read"


class ArticleCreate(BaseModel):
    """Schema for creating a new article."""
    url: HttpUrl
    tags: List[str] = Field(default_factory=list)
    priority: Priority = Priority.MEDIUM


class ArticleUpdate(BaseModel):
    """Schema for updating an existing article."""
    title: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[List[str]] = None
    priority: Optional[Priority] = None
    status: Optional[Status] = None


class Article(BaseModel):
    """Full article model with all metadata."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    url: str
    title: str
    summary: str
    source: str
    date_published: Optional[str] = None
    date_added: datetime = Field(default_factory=datetime.now)
    tags: List[str] = Field(default_factory=list)
    priority: Priority = Priority.MEDIUM
    status: Status = Status.UNREAD

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
