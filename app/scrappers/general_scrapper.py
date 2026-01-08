import os
import asyncio
import re
import feedparser
import nest_asyncio
import requests
from datetime import datetime
from typing import Annotated, List, Optional, TypedDict
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# Playwright Imports
from playwright.async_api import async_playwright

nest_asyncio.apply()
load_dotenv()

# --- 1. Refactored Pydantic Models ---

class ArticleRecord(BaseModel):
    article_name: str = Field(description="The full title of the article")
    source_link: str = Field(description="The original URL of the article")
    published_date: str = Field(description="The date the article was published")
    full_content: str = Field(description="The entire text content of the article")
    source_type: Optional[str] = Field(default="general", description="The source category (e.g., openai, anthropic)")

class ArticleBatch(BaseModel):
    """Output schema for SQL-ready data storage"""
    articles: List[ArticleRecord] = Field(description="List of fully scraped article records")

class DiscoveryOutput(BaseModel):
    urls: List[str] = Field(description="List of resolved RSS feed URLs")

# --- 2. State Definition ---

def overwrite(old: Optional[any], new: Optional[any]):
    return new

class ScraperState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    resolved_urls: Annotated[List[str], overwrite]
    # Stores intermediate data before the full scrape
    raw_articles: Annotated[List[dict], overwrite] 
    # Final Pydantic output
    final_records: Annotated[Optional[ArticleBatch], overwrite]
    top_n: Annotated[int, overwrite]

# --- 3. LLM Setup ---

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
discovery_parser = PydanticOutputParser(pydantic_object=DiscoveryOutput)
record_parser = PydanticOutputParser(pydantic_object=ArticleBatch)

# --- 4. Node Functions ---

def discovery_node(state: ScraperState):
    """Identifies RSS URLs from prompt or directory."""
    user_input = state["messages"][-1].content.lower()
    RSS_DIRECTORY = {
        "openai": "https://openai.com/news/rss.xml",
        "anthropic news": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml",
        "anthropic research": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml"
    }
    
    found_urls = re.findall(r'https?://\S+', user_input)
    for name, url in RSS_DIRECTORY.items():
        if name in user_input and url not in found_urls:
            found_urls.append(url)
            
    if not found_urls:
        prompt = f"Find the RSS feed URL for: {user_input}\n{discovery_parser.get_format_instructions()}"
        response = llm.invoke(prompt)
        found_urls = discovery_parser.parse(response.content).urls

    return {"resolved_urls": list(set(found_urls))}

def fetch_rss_node(state: ScraperState):
    """Fetches article metadata (Title, Link, Date) from RSS."""
    n = state.get("top_n", 2)
    raw_list = []
    headers = {'User-Agent': 'Mozilla/5.0'}

    for url in state["resolved_urls"]:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:n]:
                # Extract date, fallback to 'Unknown' if missing
                pub_date = entry.get('published', entry.get('updated', datetime.now().strftime("%Y-%m-%d")))
                
                raw_list.append({
                    "title": entry.get('title', 'No Title'),
                    "link": entry.get('link'),
                    "date": pub_date
                })
        except Exception as e:
            print(f"RSS Fetch Error: {e}")
    
    return {"raw_articles": raw_list}

async def scrape_full_content_node(state: ScraperState):
    """Performs deep scrape of every article to get the entire content."""
    final_articles = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        for raw in state["raw_articles"]:
            try:
                print(f"Deep Scraping: {raw['title']}")
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
                
                # Speed Optimization: Stop heavy media
                await page.route("**/*", lambda route: route.abort() 
                    if route.request.resource_type in ["image", "media", "font"] 
                    else route.continue_()
                )

                # Wait for HTML structure
                await page.goto(raw['link'], wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3) # Wait for JS text hydration
                
                # Capture the entire body text
                full_text = await page.inner_text('body')
                
                # Create the ArticleRecord object
                final_articles.append(ArticleRecord(
                    article_name=raw['title'],
                    source_link=raw['link'],
                    published_date=raw['date'],
                    full_content=full_text if full_text else "Content extraction failed."
                ))
                
                await context.close()
            except Exception as e:
                print(f"Scrape Error on {raw['link']}: {e}")
                
        await browser.close()
        
    return {"final_records": ArticleBatch(articles=final_articles)}

# --- 5. Graph Construction ---

builder = StateGraph(ScraperState)

builder.add_node("discovery", discovery_node)
builder.add_node("fetcher", fetch_rss_node)
builder.add_node("scraper", scrape_full_content_node)

builder.add_edge(START, "discovery")
builder.add_edge("discovery", "fetcher")
builder.add_edge("fetcher", "scraper")
builder.add_edge("scraper", END)

workflow = builder.compile()

# --- 6. Execution ---

async def main():
    user_prompt = "Get full content for the latest OpenAI and Anthropic news"
    print("--- Starting Full-Content Extraction Agent ---")
    
    inputs = {
        "messages": [HumanMessage(content=user_prompt)],
        "top_n": 1
    }
    
    result = await workflow.ainvoke(inputs)
    
    if result.get("final_records"):
        for record in result["final_records"].articles:
            print("\n" + "="*50)
            print(f"NAME: {record.article_name}")
            print(f"DATE: {record.published_date}")
            print(f"URL:  {record.source_link}")
            print("-" * 50)
            # Printing first 500 chars of full content for verification
            print(f"CONTENT PREVIEW: {record.full_content[:500]}...")

if __name__ == "__main__":
    asyncio.run(main())