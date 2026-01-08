from datetime import date, datetime
from typing import Optional, Union, List
from sqlalchemy.orm import Session
# Added ScrapedArticle to the imports
from app.database.models import (
    OpenAIArticle, 
    AnthropicArticle, 
    YouTubeVideo, 
    ArticleSummary, 
    DailyDigest,
    ScrapedArticle  # Assuming you added the model we discussed
)

class Repository:
    def __init__(self, session: Session):
        self.session = session

    # --- NEW: General Scraper Integration ---
    def save_general_article(self, article_data) -> bool:
        """
        Saves an article from the new general_scrapper.py logic.
        Expects an object with: article_name, source_link, published_date, full_content, and source_type.
        Returns True if saved, False if duplicate.
        """
        # Deduplication check using the URL
        exists = self.session.query(ScrapedArticle).filter_by(source_link=str(article_data.source_link)).first()
        
        if not exists:
            # Handle date conversion if it's a string, otherwise use as is
            pub_date = article_data.published_date
            if isinstance(pub_date, str):
                try:
                    # Attempt to parse common RSS date formats if necessary
                    from dateutil import parser
                    pub_date = parser.parse(pub_date)
                except Exception:
                    pub_date = datetime.now()

            new_entry = ScrapedArticle(
                article_name=article_data.article_name,
                source_link=str(article_data.source_link),
                source_type=getattr(article_data, 'source_type', 'general'),
                published_date=pub_date,
                full_content=article_data.full_content
            )
            self.session.add(new_entry)
            self.session.commit()
            return True
        return False

    def get_all_scraped_articles(self, limit: int = 10) -> List[ScrapedArticle]:
        """Retrieves latest scraped articles for the advanced summary workflow."""
        return self.session.query(ScrapedArticle).order_by(ScrapedArticle.created_at.desc()).limit(limit).all()

    # --- 1. OpenAI (Legacy/Specific) ---
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

    # --- 2. Anthropic (Legacy/Specific) ---
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
        """
        exists = self.session.query(YouTubeVideo).filter_by(video_id=video.video_id).first()
        if not exists:
            new_entry = YouTubeVideo(
                video_id=video.video_id,
                title=video.title,
                url=video.link,
                published_at=video.published,
                transcript=None  
            )
            self.session.add(new_entry)
            self.session.commit()
            return True
        return False

    def update_youtube_transcript(self, video_id: str, transcript_text: str) -> bool:
        video = self.session.query(YouTubeVideo).filter_by(video_id=video_id).first()
        if video:
            video.transcript = transcript_text
            self.session.commit()
            return True
        return False

    # --- 4. Article Summaries ---
    def save_summary(self, source_id: int, source_type: str, title: str, source_url: str, summary_text: str, impact_score: int) -> bool:
        exists = self.session.query(ArticleSummary).filter_by(
            source_id=source_id, 
            source_type=source_type
        ).first()

        if not exists:
            new_summary = ArticleSummary(
                source_id=source_id,
                source_type=source_type,
                title=title,
                source_url=source_url,
                summary=summary_text,
                impact_score=impact_score
            )
            self.session.add(new_summary)
            self.session.commit()
            return True
        return False

    def update_impact_score(self, summary_id: int, score: int) -> bool:
        summary_item = self.session.query(ArticleSummary).filter_by(id=summary_id).first()
        if summary_item:
            summary_item.impact_score = score
            self.session.commit()
            return True
        return False

    # --- 5. Daily Digest ---
    def save_daily_digest(self, title: str, content: str, digest_date: Optional[date] = None) -> bool:
        if digest_date is None:
            digest_date = date.today()

        exists = self.session.query(DailyDigest).filter_by(date=digest_date).first()
        
        if not exists:
            new_digest = DailyDigest(
                date=digest_date,
                title=title,
                content=content
            )
            self.session.add(new_digest)
            self.session.commit()
            return True
        return False