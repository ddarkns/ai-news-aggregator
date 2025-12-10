"""YouTube scraping helpers (transcripts + channel feeds)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import parse_qs, urlparse
import re

import feedparser
import requests
from youtube_transcript_api import YouTubeTranscriptApi

from pydantic import BaseModel, Field


class Transcript(BaseModel):
    """Simple transcript model with the raw snippets concatenated."""

    video_id: str
    text: str = Field(default="")

    @classmethod
    def from_raw(cls, video_id: str, raw_snippets: List[dict], delimiter: str = " ") -> "Transcript":
        text_parts = []
        for snippet in raw_snippets:
            part = str(snippet.text).strip()
            if part:
                text_parts.append(part)
        return cls(video_id=video_id, text=delimiter.join(text_parts))


class Video(BaseModel):
    """Minimal video metadata."""

    title: str = ""
    video_id: str = ""
    published: Optional[datetime] = None
    link: Optional[str] = None


class YouTubeScraper:
    """Minimal wrapper around youtube-transcript-api, feedparser, and requests."""

    def __init__(self, session: Optional[requests.Session] = None) -> None:
        self.session = session or requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; transcript-scraper/1.0)"}
        )
        self.transcript_client = YouTubeTranscriptApi()

    # Transcript helpers

    def fetch_transcript(self, video_id: str) -> Transcript:
        """Return transcript as a simple Pydantic model."""
        langs=self.transcript_client.list(video_id)
        lang = langs.find_transcript(['de','en'])
        raw = self.transcript_client.fetch(video_id,languages=[lang])  # type: ignore[attr-defined]
        return Transcript.from_raw(video_id, raw)

    # ID extractors

    @staticmethod
    def extract_video_id(youtube_url: str) -> str:
        """Extract the YouTube video ID from a full URL."""
        parsed = urlparse(youtube_url)
        if parsed.hostname in {"youtu.be"}:
            return parsed.path.lstrip("/")
        if parsed.path == "/watch":
            return parse_qs(parsed.query).get("v", [""])[0]
        return parsed.path.rsplit("/", 1)[-1]

    def extract_channel_id(self, channel_url: str) -> str:
        """Extract channel ID (UC...) from a channel URL (e.g., handle URL)."""
        try:
            resp = self.session.get(channel_url, timeout=10)
            resp.raise_for_status()
        except Exception:
            return ""

        match = re.search(r'"channelId":"(UC[0-9A-Za-z_-]{21,})"', resp.text) or re.search(
            r'"externalId":"(UC[0-9A-Za-z_-]{21,})"', resp.text
        )
        return match.group(1) if match else ""

    # Feed helpers

    def get_recent_videos(
        self, channel_id: str, within: timedelta = timedelta(days=1), verbose: bool = False
    ) -> List[Video]:
        """Return recent videos for a channel within the given time window."""
        if not channel_id:
            if verbose:
                print("[feed] missing channel_id; skipping fetch")
            return []

        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        cutoff = datetime.now(timezone.utc) - within
        feed = feedparser.parse(feed_url)
        if verbose:
            print(f"[feed] url={feed_url} entries={len(feed.entries)} cutoff={cutoff.isoformat()}")

        recent: List[Video] = []
        for entry in feed.entries:
            published = getattr(entry, "published_parsed", None) or getattr(
                entry, "updated_parsed", None
            )
            if not published:
                continue
            published_dt = datetime(*published[:6], tzinfo=timezone.utc)
            if published_dt >= cutoff:
                recent.append(
                    Video(
                        title=entry.get("title", ""),
                        video_id=entry.get("yt_videoid", ""),
                        published=published_dt,
                        link=entry.get("link", ""),
                    )
                )
        if verbose:
            print(f"[feed] recent={len(recent)}")
        return recent


if __name__ == "__main__":
    scraper = YouTubeScraper()

    # Transcript demo
    sample_url = "https://www.youtube.com/watch?v=E8zpgNPx8jE"
    video_id = scraper.extract_video_id(sample_url)
    print(f"Video ID: {video_id}")
    
    
    transcript = scraper.fetch_transcript("xcNwd0B_EL0")
    print(f"Transcript length (chars): {len(transcript.text)}")
    print(transcript.text[:500])

    # Recent videos demo
    sample_channel_id = scraper.extract_channel_id("https://www.youtube.com/@daveebbelaar")
    print(f"Channel ID: {sample_channel_id}")
    recent = scraper.get_recent_videos(sample_channel_id, within=timedelta(days=30), verbose=True)
    print(f"Recent videos in last 24h: {len(recent)}")
    for video in recent[:3]:
        print(f"- {video.title} ({video.video_id})")
