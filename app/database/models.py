from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Text, DateTime, Date, Integer, func, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime, date
from sqlalchemy import Integer, String, Text, DateTime, Date, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase

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

# --- 4. Article Summaries (New) ---
class ArticleSummary(Base):
    __tablename__ = "article_summaries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Context Linking
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # --- NEW FIELDS ---
    title: Mapped[str] = mapped_column(String(255), nullable=False)  # Stores the article title snapshot
    source_url: Mapped[str] = mapped_column(String(500), nullable=False) # Stores the direct link
    # ------------------

    summary: Mapped[str] = mapped_column(Text, nullable=False)
    impact_score: Mapped[int] = mapped_column(Integer, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    __table_args__ = (
        UniqueConstraint('source_id', 'source_type', name='uix_source_summary'),
    )

# --- 5. Daily Digest (Updated) ---
class DailyDigest(Base):
    __tablename__ = "daily_digests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, unique=True, index=True, default=func.current_date())
    
    # --- NEW FIELD ---
    title: Mapped[str] = mapped_column(String(255), nullable=False) # e.g., "AI Breakthroughs: GPT-5 Rumors & More"
    # -----------------

    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

# --- Unified News Table ---
# This model captures all the fields required by your new Pydantic schema
class ScrapedArticle(Base):
    """
    Main table for storing full article content for later processing.
    """
    __tablename__ = "scraped_articles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Core Metadata
    article_name: Mapped[str] = mapped_column(String(500), nullable=False)
    source_link: Mapped[str] = mapped_column(String(500), unique=True, index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), index=True) # e.g., 'openai', 'anthropic_research'
    
    # Dates
    published_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # High-Fidelity Content
    full_content: Mapped[str] = mapped_column(Text, nullable=False) 

    def __repr__(self):
        return f"<Article(name={self.article_name}, source={self.source_type})>"


