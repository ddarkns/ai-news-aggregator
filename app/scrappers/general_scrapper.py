import os
import asyncio
import re
import feedparser
import nest_asyncio
import requests
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

# --- 1. Prebuilt RSS Directory (Recommendations) ---
RSS_DIRECTORY = {
    "openai": "https://openai.com/news/rss.xml",
    "anthropic news": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml",
    "anthropic research": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml",
    "techcrunch": "https://techcrunch.com/feed/",
    "nasa": "https://www.nasa.gov/news-release/feed/",
    "verge": "https://www.theverge.com/rss/index.xml",
    "wired": "https://www.wired.com/feed/rss",
    "ycombinator": "https://news.ycombinator.com/rss"
}

# --- 2. Pydantic Models ---

class ArticleData(BaseModel):
    title: str
    link: str
    summary: str
    full_content: Optional[str] = None

class FileContent(BaseModel):
    file_name: str = Field(description="Name of the file with extension")
    content: str = Field(description="Formatted text content with source URLs.")

class ScraperOutput(BaseModel):
    files: List[FileContent] = Field(description="List of files to create")

class DiscoveryOutput(BaseModel):
    urls: List[str] = Field(description="List of resolved RSS feed URLs")

# --- 3. State Definition ---

def overwrite(old: Optional[any], new: Optional[any]):
    return new

class ScraperState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    resolved_urls: Annotated[List[str], overwrite]
    articles: Annotated[List[ArticleData], overwrite]
    final_output: Annotated[Optional[ScraperOutput], overwrite]
    top_n: Annotated[int, overwrite]

# --- 4. LLM & Tools Setup ---

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
discovery_parser = PydanticOutputParser(pydantic_object=DiscoveryOutput)
file_parser = PydanticOutputParser(pydantic_object=ScraperOutput)

# --- 5. Node Functions ---

def discovery_node(state: ScraperState):
    """Automatically finds RSS feeds based on names or raw URLs."""
    user_input = state["messages"][-1].content.lower()
    found_urls = re.findall(r'https?://\S+', user_input)
    
    # Check against prebuilt directory
    for name, url in RSS_DIRECTORY.items():
        if name in user_input:
            if url not in found_urls:
                found_urls.append(url)
    
    # Use AI for unknown sources
    if not found_urls:
        prompt = f"Find the RSS feed URL for: {user_input}\n{discovery_parser.get_format_instructions()}"
        response = llm.invoke(prompt)
        parsed = discovery_parser.parse(response.content)
        found_urls.extend(parsed.urls)

    return {"resolved_urls": list(set(found_urls))}

def fetch_rss_node(state: ScraperState):
    n = state.get("top_n", 2)
    found_articles = []
    headers = {'User-Agent': 'Mozilla/5.0'}

    for url in state["resolved_urls"]:
        try:
            print(f"Fetching RSS: {url}")
            resp = requests.get(url, headers=headers, timeout=10)
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:n]:
                found_articles.append(ArticleData(
                    title=entry.get('title', 'No Title'),
                    link=entry.get('link', url),
                    summary=entry.get('summary', '')[:300]
                ))
        except Exception as e:
            print(f"Error fetching {url}: {e}")
    return {"articles": found_articles}

async def scrape_content_node(state: ScraperState):
    """Scrapes content with improved timeouts and resource blocking to prevent hangs."""
    updated_articles = []
    async with async_playwright() as p:
        # Launch browser with automation bypass
        browser = await p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        
        for article in state["articles"]:
            try:
                print(f"Scraping: {article.title}")
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
                )
                page = await context.new_page()

                # Optimization: Block heavy media to speed up loading
                await page.route("**/*", lambda route: route.abort() 
                    if route.request.resource_type in ["image", "media", "font"] 
                    else route.continue_()
                )

                # Wait for HTML (domcontentloaded) instead of Network Idle to avoid hangs
                await page.goto(article.link, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3) # Small pause for JS content hydration
                
                content = await page.inner_text('body')
                article.full_content = content[:6000] if content else article.summary
                await context.close()
            except Exception as e:
                print(f"Skipping {article.link} due to timeout/error: {e}")
                article.full_content = article.summary
            updated_articles.append(article)
        await browser.close()
    return {"articles": updated_articles}

def format_report_node(state: ScraperState):
    llm_json = llm.bind(response_format={"type": "json_object"})
    context = ""
    for i, a in enumerate(state["articles"]):
        context += f"ENTRY {i}\nTITLE: {a.title}\nSOURCE: {a.link}\nCONTENT: {a.full_content}\n\n"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a News Editor. Summarize these articles deeply. Include source URLs. {format_instructions}"),
        ("human", f"DATA:\n{context}")
    ]).format_prompt(format_instructions=file_parser.get_format_instructions())
    
    response = llm_json.invoke(prompt.to_messages())
    return {"final_output": file_parser.parse(response.content)}

# --- Graph Construction ---
builder = StateGraph(ScraperState)
builder.add_node("discovery", discovery_node)
builder.add_node("fetcher", fetch_rss_node)
builder.add_node("scraper", scrape_content_node)
builder.add_node("formatter", format_report_node)

builder.add_edge(START, "discovery")
builder.add_edge("discovery", "fetcher")
builder.add_edge("fetcher", "scraper")
builder.add_edge("scraper", "formatter")
builder.add_edge("formatter", END)

workflow = builder.compile()

# --- Execution ---
async def main():
    # TEST PROMPT
    user_prompt = "Get the latest updates from OpenAI news, Anthropic news, and Anthropic research."
    print("--- Starting AI-Discovery Scraper ---")
    
    inputs = {
        "messages": [HumanMessage(content=user_prompt)],
        "top_n": 1
    }
    
    final_state = await workflow.ainvoke(inputs)
    
    if final_state.get("final_output"):
        for file in final_state["final_output"].files:
            print(f"\nFILENAME: {file.file_name}\n{'='*40}\n{file.content}")

if __name__ == "__main__":
    asyncio.run(main())