import os
import sys
import asyncio
import re
import feedparser
import nest_asyncio
import requests
from datetime import datetime
from typing import Annotated, List, Optional, TypedDict
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from playwright.async_api import async_playwright

from app.database.connection import SessionLocal
from app.database.repository import Repository
from app.database.create_tables import init_db
from agents2.profile import MY_PROFILE  # Ensure this import is correct

nest_asyncio.apply()
load_dotenv()

# --- 1. Models ---
class ArticleRecord(BaseModel):
    article_name: str
    source_link: str
    published_date: str
    full_content: str
    source_type: Optional[str] = "general"

class ArticleBatch(BaseModel):
    articles: List[ArticleRecord]

class DiscoveryOutput(BaseModel):
    urls: List[str]

# --- 2. State ---
def overwrite(old, new): return new

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    user_query: Annotated[str, overwrite]
    discovered_urls: Annotated[List[str], overwrite]
    raw_articles: Annotated[List[dict], overwrite]
    final_records: Annotated[Optional[ArticleBatch], overwrite]
    top_n: Annotated[int, overwrite]

# --- 3. Nodes ---

async def discovery_node(state: AgentState):
    """
    Router Node: Processes the query against a local directory AND 
    uses AI to resolve multiple sources simultaneously.
    """
    # ⏱️ Rate limit protection heartbeat
    await asyncio.sleep(2)
    
    query = state.get("user_query", "").lower()
    
    # 1. Base RSS Directory
    RSS_DIRECTORY = {
        # Tech / AI
        "openai": "https://openai.com/news/rss.xml",
        "anthropic news": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml",
        "anthropic research": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml",
        "techcrunch": "https://techcrunch.com/feed/",
        "the verge": "https://www.theverge.com/rss/index.xml",
        
        # Indian News
        "times of india": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "the hindu": "https://www.thehindu.com/news/national/feeder/default.rss",
        "hindustan times": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
        "ndtv": "http://feeds.feedburner.com/ndtvnews-top-stories",
        "moneycontrol": "https://www.moneycontrol.com/rss/latestnews.xml"
    }
    
    # 🔗 DYNAMIC SYNC: Append custom URLs from the user profile
    if hasattr(MY_PROFILE, 'custom_sources') and MY_PROFILE.custom_sources:
        RSS_DIRECTORY.update(MY_PROFILE.custom_sources)
        print(f"🔄 Synced {len(MY_PROFILE.custom_sources)} custom sources from Profile.")
    
    # 2. Strategy: Let the LLM be the "Intelligence Router"
    parser = JsonOutputParser(pydantic_object=DiscoveryOutput)
    
    prompt = f"""
    You are a professional News Router. 
    Analyze the user request and provide the correct RSS feed URLs.
    
    USER REQUEST: "{query}"
    
    LOCAL DIRECTORY (including verified user sources):
    {RSS_DIRECTORY}
    
    INSTRUCTIONS:
    1. Identify ALL news sources mentioned or relevant to the request.
    2. If a source is in the LOCAL DIRECTORY, use that URL.
    3. If a source is requested that is NOT in the directory, find the most likely official RSS URL.
    
    {parser.get_format_instructions()}
    IMPORTANT: Return ONLY raw JSON.
    """
    
    print("🧠 Routing query to identify all requested sources...")
    response = await llm.ainvoke(prompt)
    
    found_urls = []
    try:
        parsed = parser.parse(response.content)
        found_urls = parsed.get("urls", [])
    except Exception:
        print("⚠️ AI Formatting error. Applying Regex fallback logic.")
        found_urls = re.findall(r'https?://\S+', response.content)
        
    for name, url in RSS_DIRECTORY.items():
        if name in query and url not in found_urls:
            found_urls.append(url)

    print(f"📡 Discovered {len(found_urls)} feed(s): {found_urls}")
    return {"discovered_urls": list(set(found_urls))}

async def fetch_rss_node(state: AgentState):
    """Fetches metadata from RSS."""
    n = state.get("top_n", 1)
    raw_list = []
    headers = {'User-Agent': 'Mozilla/5.0'}
    for url in state["discovered_urls"]:
        try:
            print(f"📡 Fetching RSS: {url}")
            resp = requests.get(url, headers=headers, timeout=10)
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:n]:
                pub_date = entry.get('published', entry.get('updated', datetime.now().strftime("%Y-%m-%d")))
                raw_list.append({
                    "title": entry.get('title', 'No Title'),
                    "link": entry.get('link'),
                    "date": pub_date
                })
        except Exception as e: 
            print(f"❌ RSS Error ({url}): {e}")
            
    return {"raw_articles": raw_list}

async def scrape_content_node(state: AgentState):
    """Performs deep scraping using standard Playwright."""
    final_articles = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        for raw in state["raw_articles"]:
            try:
                print(f"🔍 Deep Scraping: {raw['title']}")
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."
                )
                page = await context.new_page()
                
                await page.route("**/*", lambda route: route.abort() 
                    if route.request.resource_type in ["image", "media", "font"] 
                    else route.continue_()
                )

                await page.goto(raw['link'], wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(4) 
                
                full_text = await page.inner_text('body')
                
                final_articles.append(ArticleRecord(
                    article_name=raw['title'],
                    source_link=raw['link'],
                    published_date=raw['date'],
                    full_content=full_text if full_text else "Content extraction failed."
                ))
                await context.close()
            except Exception as e: 
                print(f"⚠️ Scrape Error: {e}")
                
        await browser.close()
    return {"final_records": ArticleBatch(articles=final_articles)}

def persistence_node(state: AgentState):
    """Saves to Postgres."""
    session = SessionLocal()
    repo = Repository(session)
    saved_count = 0
    if state["final_records"]:
        for record in state["final_records"].articles:
            if repo.save_general_article(record):
                saved_count += 1
                print(f"✅ DB Saved: {record.article_name[:40]}...")
                
    session.close()
    return {"messages": [AIMessage(content=f"Workflow complete. Saved {saved_count} articles.")]}

# --- 4. Graph Construction ---
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

builder = StateGraph(AgentState)
builder.add_node("discovery", discovery_node)
builder.add_node("fetcher", fetch_rss_node)
builder.add_node("scraper", scrape_content_node)
builder.add_node("persistence", persistence_node)

builder.add_edge(START, "discovery")
builder.add_edge("discovery", "fetcher")
builder.add_edge("fetcher", "scraper")
builder.add_edge("scraper", "persistence")
builder.add_edge("persistence", END)

scrapper_agent = builder.compile()

if __name__ == "__main__":
    async def run_test():
        init_db()
        test_input = {
            "user_query": "Reuters, FT, and tell me if there is anything from Anthropic", 
            "top_n": 1
        }
        print("🚀 Starting Agent...")
        result = await scrapper_agent.ainvoke(test_input)
        print(f"\nFinal Status: {result['messages'][-1].content}")
        
    asyncio.run(run_test())
  