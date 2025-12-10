"""Anthropic News RSS scraper."""

from __future__ import annotations
from typing import List, Optional
import feedparser
from pydantic import BaseModel, HttpUrl
from datetime import datetime

import nest_asyncio
import asyncio
import textwrap

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

ANTHROPIC_RSS_URL = "https://rss.app/feeds/gY78yQ2iD3mfNsim.xml"


class AnthropicArticle(BaseModel):
    title: str
    link: HttpUrl
    summary: Optional[str] = None
    published: Optional[datetime] = None

    @classmethod
    def from_entry(cls, entry: feedparser.FeedParserDict) -> "AnthropicArticle":
        published = getattr(entry, "published_parsed", None)
        published_dt = datetime(*published[:6]) if published else None
        return cls(
            title=entry.get("title", "").strip(),
            link=entry.get("link"),
            summary=entry.get("description"),
            published=published_dt,
        )


class AnthropicScraper:
    """Fetches articles from Anthropic's News RSS feed."""

    def __init__(self, rss_url: str = ANTHROPIC_RSS_URL, headless: bool = False) -> None:
        self.rss_url = rss_url
        self.headless = headless

    def fetch_articles(self, limit: Optional[int] = None) -> List[AnthropicArticle]:
        feed = feedparser.parse(self.rss_url)
        entries = feed.entries[:limit] if limit else feed.entries
        return [AnthropicArticle.from_entry(entry) for entry in entries]

    def url_to_markdown(self, url: str, wait_time: int = 20) -> Optional[str]:
        """
        Convert a webpage URL to Markdown format using Playwright browser automation.
        
        Args:
            url: The URL of the webpage to convert
            wait_time: Time to wait for page to load (seconds)
            
        Returns:
            Markdown string if successful, None if conversion fails
        """
        try:
            # Run the async function synchronously
            return asyncio.run(self._url_to_text_async(url, wait_time))
        except Exception as e:
            print(f"Error converting URL to markdown: {e}")
            return None

    async def _url_to_text_async(self, url: str, wait_time: int) -> Optional[str]:
        """
        Async helper function to convert URL to text using Playwright.
        """
        try:
            from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
            from langchain_community.tools.playwright.utils import create_async_playwright_browser
            
            # Create async browser
            async_browser = create_async_playwright_browser(headless=self.headless)
            
            # Create toolkit and tools
            toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
            tools = toolkit.get_tools()
            tool_dict = {tool.name: tool for tool in tools}
            
            # Get navigation and extraction tools
            navigate_tool = tool_dict.get("navigate_browser")
            extract_text_tool = tool_dict.get("extract_text")
            
            if not navigate_tool or not extract_text_tool:
                print("Error: Required tools not found")
                return None
            
            # Navigate to URL
            await navigate_tool.arun({"url": url})
            
            # Wait for page to load
            await asyncio.sleep(wait_time)
            
            # Extract text
            text = await extract_text_tool.arun({})
            
            return text
            
        except Exception as e:
            print(f"Async error: {e}")
            return None

    def batch_to_markdown(self, articles: List[AnthropicArticle], max_articles: Optional[int] = None) -> List[str]:
        """
        Convert multiple article URLs to markdown.
        
        Args:
            articles: List of AnthropicArticle objects
            max_articles: Maximum number of articles to process
            
        Returns:
            List of markdown strings
        """
        results = []
        articles_to_process = articles[:max_articles] if max_articles else articles
        
        for i, article in enumerate(articles_to_process, 1):
            print(f"Processing article {i}/{len(articles_to_process)}: {article.title}")
            markdown = self.url_to_markdown(str(article.link), wait_time=15)
            results.append(markdown)
            
            # Small delay between requests to avoid rate limiting
            import time
            time.sleep(2)
        
        return results


if __name__ == "__main__":
    scraper = AnthropicScraper(headless=False)  # Set headless=False to see browser
    
    # Get articles
    articles = scraper.fetch_articles(limit=2)
    
    # Print what we got from RSS
    print(f"Found {len(articles)} articles from RSS feed")
    for i, article in enumerate(articles, 1):
        print(f"\n{i}. {article.title}")
        print(f"   Published: {article.published}")
        print(f"   Link: {article.link}")
        if article.summary:
            print(f"   Summary: {article.summary[:150]}...")
    
    # Convert first article to markdown
    if articles:
        first_article_url = str(articles[0].link)
        print(f"\n\nConverting: {articles[0].title}")
        print(f"URL: {first_article_url}")
        
        markdown = scraper.url_to_markdown(first_article_url, wait_time=15)
        
        if markdown:
            print(f"\nSuccessfully converted! Length: {len(markdown)} characters")
            print("\nFirst 500 characters:")
            print("-" * 50)
            print(textwrap.fill(markdown[:500]))
            print("-" * 50)
            
            # Save to file
            with open("anthropic_article.md", "w", encoding="utf-8") as f:
                f.write(markdown)
            print("\nSaved to 'anthropic_article.md'")
        else:
            print("Failed to convert URL to markdown")
    else:
        print("No articles found in RSS feed")