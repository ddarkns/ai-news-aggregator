from datetime import date
from typing import Optional, Union
from sqlalchemy.orm import Session
# Make sure to import the new models here
from app.database.models import (
    OpenAIArticle, 
    AnthropicArticle, 
    YouTubeVideo, 
    ArticleSummary, 
    DailyDigest
)

class Repository:
    def __init__(self, session: Session):
        self.session = session

    # --- 1. OpenAI ---
    def save_openai(self, article, content: str) -> bool:
        """
        Saves an OpenAI article if it doesn't already exist.
        Returns True if saved, False if duplicate.
        """
        exists = self.session.query(OpenAIArticle).filter_by(url=str(article.link)).first()
        if not exists:
            new_entry = OpenAIArticle(
                title=article.title,
                url=str(article.link),
                content=content,
                published_at=article.published
            )
            self.session.add(new_entry)
            self.session.commit()
            return True
        return False

    # --- 2. Anthropic ---
    def save_anthropic(self, source_type: str, article, content: str) -> bool:
        """
        Saves an Anthropic article (GitHub or Research) if it doesn't exist.
        Returns True if saved, False if duplicate.
        """
        exists = self.session.query(AnthropicArticle).filter_by(url=str(article.link)).first()
        if not exists:
            new_entry = AnthropicArticle(
                source_type=source_type,  # e.g., 'github' or 'research'
                title=article.title,
                url=str(article.link),
                content=content,
                published_at=article.published
            )
            self.session.add(new_entry)
            self.session.commit()
            return True
        return False

    # --- 3. YouTube ---
    def save_youtube(self, video) -> bool:
        """
        Saves YouTube metadata (Transcript is deliberately skipped/None).
        Returns True if saved, False if duplicate.
        """
        exists = self.session.query(YouTubeVideo).filter_by(video_id=video.video_id).first()
        if not exists:
            new_entry = YouTubeVideo(
                video_id=video.video_id,
                title=video.title,
                url=video.link,
                published_at=video.published,
                transcript=None  # Explicitly set to None to fetch later
            )
            self.session.add(new_entry)
            self.session.commit()
            return True
        return False

    def update_youtube_transcript(self, video_id: str, transcript_text: str) -> bool:
        """
        Updates an existing YouTube video record with its transcript.
        Returns True if updated, False if video ID not found.
        """
        video = self.session.query(YouTubeVideo).filter_by(video_id=video_id).first()
        if video:
            video.transcript = transcript_text
            self.session.commit()
            return True
        return False

    # --- 4. Article Summaries (New) ---
    def save_summary(self, source_id: int, source_type: str, title: str, source_url: str, summary_text: str, impact_score: int) -> bool:
        exists = self.session.query(ArticleSummary).filter_by(
            source_id=source_id, 
            source_type=source_type
        ).first()

        if not exists:
            new_summary = ArticleSummary(
                source_id=source_id,
                source_type=source_type,
                title=title,           # <--- Saving Title
                source_url=source_url, # <--- Saving URL
                summary=summary_text,
                impact_score=impact_score
            )
            self.session.add(new_summary)
            self.session.commit()
            return True
        return False

    # --- 5. Daily Digest (New) ---
    def save_daily_digest(self, content: str, digest_date: Optional[date] = None) -> bool:
        """
        Saves the Daily Digest. 
        If digest_date is not provided, defaults to today's date.
        Returns True if saved, False if a digest for that date already exists.
        """
        if digest_date is None:
            digest_date = date.today()

        exists = self.session.query(DailyDigest).filter_by(date=digest_date).first()
        
        if not exists:
            new_digest = DailyDigest(
                date=digest_date,
                content=content
            )
            self.session.add(new_digest)
            self.session.commit()
            return True
        return False
    def update_impact_score(self, summary_id: int, score: int) -> bool:
        """
        Updates the impact_score for a specific article summary.
        """
        summary_item = self.session.query(ArticleSummary).filter_by(id=summary_id).first()
        if summary_item:
            summary_item.impact_score = score
            self.session.commit()
            return True
        return False
    def save_daily_digest(self, title: str, content: str, digest_date: Optional[date] = None) -> bool:
        """
        Saves the Daily Digest. 
        Requires a TITLE and CONTENT.
        """
        if digest_date is None:
            digest_date = date.today()

        exists = self.session.query(DailyDigest).filter_by(date=digest_date).first()
        
        if not exists:
            new_digest = DailyDigest(
                date=digest_date,
                title=title,    # <--- NOW ADDED
                content=content
            )
            self.session.add(new_digest)
            self.session.commit()
            return True
        return False