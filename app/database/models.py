from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

# --- 1. OpenAI Table ---
class OpenAIArticle(Base):
    __tablename__ = "openai_articles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    content: Mapped[str] = mapped_column(Text)  # Markdown content
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

# --- 2. Anthropic Table ---
class AnthropicArticle(Base):
    __tablename__ = "anthropic_articles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_type: Mapped[str] = mapped_column(String(50)) # e.g., 'github', 'research'
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

# --- 3. YouTube Table ---
class YouTubeVideo(Base):
    __tablename__ = "youtube_videos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    video_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(500))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Transcript is optional (to be filled later)
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())