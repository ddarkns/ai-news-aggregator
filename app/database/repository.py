from sqlalchemy.orm import Session
from app.database.models import OpenAIArticle, AnthropicArticle, YouTubeVideo

class Repository:
    def __init__(self, session: Session):
        self.session = session

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