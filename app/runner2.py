import os
import sys
import asyncio
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage

# Ensure project root is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.connection import get_db
from app.database.repository import Repository
from app.database.create_tables import init_db

# Import the workflow from your general_scrapper.py
from app.scrappers.general_scrapper import workflow

# --- UPDATED MODEL: This must match what is in your general_scrapper.py ---
class ArticleRecord(BaseModel):
    article_name: str = Field(description="The full title of the article")
    source_link: str = Field(description="The original URL of the article")
    published_date: str = Field(description="The date the article was published")
    full_content: str = Field(description="The entire text content of the article")
    # Added field to prevent Pydantic assignment errors
    source_type: Optional[str] = Field(default="general", description="Source category")

async def main():
    # 1. Initialize Database and Session
    print("🔄 Connecting to database and ensuring tables exist...")
    init_db() 
    db_gen = get_db()
    session = next(db_gen)
    repo = Repository(session)
    
    # 2. Setup Scraper Inputs
    # This prompt triggers the AI Discovery node in your graph
    user_prompt = "Get full content for the latest OpenAI news, Anthropic news, and Anthropic research"
    print(f"--- Starting Unified Scraped Articles Pipeline ---")
    
    inputs = {
        "messages": [HumanMessage(content=user_prompt)],
        "top_n": 1
    }
    
    try:
        # 3. Invoke General Scrapper Workflow
        # This executes discovery -> fetcher -> scraper nodes
        result = await workflow.ainvoke(inputs)
        
        # 4. Save results to the unified 'scraped_articles' table
        if result.get("final_records"):
            articles = result["final_records"].articles
            print(f"✅ Scraper finished. Found {len(articles)} articles.")

            for record in articles:
                print("\n" + "="*50)
                print(f"ARTICLE: {record.article_name}")
                print(f"URL:     {record.source_link}")
                
                # Determine source_type for the unified general table
                source_url = record.source_link.lower()
                if "openai.com" in source_url:
                    record.source_type = "openai"
                elif "anthropic.com" in source_url:
                    # Specific check for research vs news sub-types
                    record.source_type = "anthropic_research" if "research" in source_url else "anthropic_news"
                else:
                    record.source_type = "general"

                # 5. COMMIT TO DB: Use the unified save method from your Repository
                # This handles deduplication by checking the URL before inserting
                saved = repo.save_general_article(record)
                
                if saved:
                    print(f"STATUS: ✅ Successfully saved to 'scraped_articles' table")
                else:
                    print(f"STATUS: ⏭️  Skipped (Duplicate URL found in DB)")
                
                print("-" * 50)
                
    except Exception as e:
        # Captures any runtime errors during the graph execution or DB commit
        print(f"❌ Critical Error in Pipeline: {e}")
    finally:
        session.close()
        print("\n--- Pipeline Execution Complete ---")

if __name__ == "__main__":
    # Because the general scraper uses Playwright (Async), main must run in an event loop
    asyncio.run(main())