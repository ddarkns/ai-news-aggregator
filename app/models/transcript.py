from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

from pydantic import BaseModel, Field


class Transcript(BaseModel):
    """Simple transcript model with the raw snippets concatenated."""

    video_id: str
    text: str = Field(default="")

    @classmethod
    def from_raw(cls, video_id: str, raw_snippets: Iterable[dict], delimiter: str = " ") -> "Transcript":
        text_parts = []
        for snippet in raw_snippets:
            part = str(snippet.get("text", "")).strip()
            if part:
                text_parts.append(part)
        return cls(video_id=video_id, text=delimiter.join(text_parts))


class Video(BaseModel):
    """Minimal video metadata."""

    title: str = ""
    video_id: str = ""
    published: Optional[datetime] = None
    link: Optional[str] = None

