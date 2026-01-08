from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Text, DateTime, Date, Integer, func, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

# --- 1. OpenAI Table (Legacy) ---
class OpenAIArticle(Base):
    __tablename__ = "openai_articles"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

# --- 2. Anthropic Table (Legacy) ---
class AnthropicArticle(Base):
    __tablename__ = "anthropic_articles"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_type: Mapped[str] = mapped_column(String(50)) 
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
    transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

# --- 4. Legacy Article Summary ---
class ArticleSummary(Base):
    __tablename__ = "article_summaries"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    source_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    impact_score: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    __table_args__ = (UniqueConstraint('source_id', 'source_type', name='uix_source_summary'),)

# --- 5. Unified News Table (Raw Content) ---
class ScrapedArticle(Base):
    __tablename__ = "scraped_articles"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    article_name: Mapped[str] = mapped_column(String(500), nullable=False)
    source_link: Mapped[str] = mapped_column(String(500), unique=True, index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), index=True)
    published_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    full_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

# --- 6. AGGREGATED SUMMARY TABLE (New for Agents2) ---
class AggregatedSummary(Base):
    __tablename__ = "aggregated_summaries"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    article_name: Mapped[str] = mapped_column(String(500), nullable=False)
    source_link: Mapped[str] = mapped_column(String(500), unique=True, index=True, nullable=False)
    published_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    impact_score: Mapped[int] = mapped_column(Integer, default=0) # Relevance score
    relevance_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

# --- 7. Daily Digest ---
class DailyDigest(Base):
    __tablename__ = "daily_digests"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, unique=True, index=True, default=func.current_date())
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())