"""Configuration settings for the scraping pipeline."""

from typing import List

class Config:
    # --- Output Settings ---
    OUTPUT_DIR: str = "output"
    
    # --- Scraper Limits ---
    # How many recent articles/videos to fetch per source
    MAX_ARTICLES_PER_SOURCE: int = 2 
    MAX_VIDEOS_PER_CHANNEL: int = 2
    
    # Days to look back for YouTube videos
    YOUTUBE_LOOKBACK_DAYS: int = 2

    # --- Sources ---
    
    # 1. OpenAI News
    OPENAI_RSS_URL: str = "https://openai.com/news/rss.xml"
    
    # 2. Anthropic News (GitHub Feed)
    ANTHROPIC_GITHUB_RSS_URL: str = "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml"
    
    # 3. Anthropic Research (RSS App)
    ANTHROPIC_RESEARCH_RSS_URL: str = "https://rss.app/feeds/gY78yQ2iD3mfNsim.xml"

    # 4. YouTube Channels to scrape
    YOUTUBE_CHANNELS: List[str] = [
        "https://www.youtube.com/@daveebbelaar",
        "https://www.youtube.com/@airevolutionx",
        # Add more channels here
    ]