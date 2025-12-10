import os
import sys
from datetime import timedelta

# Fix path to allow running from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Config
from app.database.connection import get_db
from app.database.repository import Repository
from app.database.create_tables import init_db

# Scrapers
from app.scrappers.openai_scraper import OpenAINewsScraper
from app.scrappers.anthropic_news_scraper import AnthropicGitHubScraper
from app.scrappers.anthrophic_research_scraper import AnthropicScraper
from app.scrappers.youtube_scraper import YouTubeScraper

def run_pipeline():
    # 1. Setup Database & Config
    cfg = Config()
    init_db()  # Ensures tables exist
    
    # Get DB Session
    db_gen = get_db()
    session = next(db_gen)
    repo = Repository(session)
    
    stats = {"openai": 0, "anthropic": 0, "youtube": 0}
    print("🚀 Starting Data Pipeline...")

    try:
        # --- 1. OpenAI ---
        print("\n--- Processing OpenAI ---")
        oa = OpenAINewsScraper(cfg.OPENAI_RSS_URL)
        for article in oa.fetch_articles(limit=cfg.MAX_ARTICLES_PER_SOURCE):
            # We fetch content immediately for articles
            md = oa.url_to_markdown(str(article.link))
            if md:
                if repo.save_openai(article, md):
                    print(f"  [DB] Saved: {article.title[:40]}...")
                    stats["openai"] += 1
                else:
                    print(f"  [DB] Skipped (Duplicate): {article.title[:40]}...")

        # --- 2. Anthropic (GitHub + Research) ---
        print("\n--- Processing Anthropic ---")
        sources = [
            (AnthropicGitHubScraper(cfg.ANTHROPIC_GITHUB_RSS_URL), "github"),
            (AnthropicScraper(cfg.ANTHROPIC_RESEARCH_RSS_URL), "research")
        ]
        for scraper, source_type in sources:
            for article in scraper.fetch_articles(limit=cfg.MAX_ARTICLES_PER_SOURCE):
                md = scraper.url_to_markdown(str(article.link))
                if md:
                    if repo.save_anthropic(source_type, article, md):
                        print(f"  [DB] Saved ({source_type}): {article.title[:40]}...")
                        stats["anthropic"] += 1
                    else:
                        print(f"  [DB] Skipped: {article.title[:40]}...")

        # --- 3. YouTube ---
        print("\n--- Processing YouTube ---")
        yt = YouTubeScraper()
        for channel_url in cfg.YOUTUBE_CHANNELS:
            print(f"  Scanning: {channel_url}")
            cid = yt.extract_channel_id(channel_url)
            
            # Corrected: Using 'within' argument for timedelta
            videos = yt.get_recent_videos(cid, within=timedelta(days=cfg.YOUTUBE_LOOKBACK_DAYS))
            
            for video in videos[:cfg.MAX_VIDEOS_PER_CHANNEL]:
                # We save ONLY metadata now (transcript=None), to be fetched later
                if repo.save_youtube(video):
                    print(f"  [DB] Saved Metadata: {video.title[:40]}...")
                    stats["youtube"] += 1
                else:
                    print(f"  [DB] Skipped Video: {video.title[:40]}...")

    finally:
        session.close()

    return stats

if __name__ == "__main__":
    results = run_pipeline()
    print("\n✅ Pipeline Done!")
    print(f"OpenAI Articles: {results['openai']}")
    print(f"Anthropic Articles: {results['anthropic']}")
    print(f"YouTube Videos: {results['youtube']}")