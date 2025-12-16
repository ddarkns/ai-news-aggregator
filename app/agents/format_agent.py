import sys
import os
import logging
from datetime import datetime, timedelta
from typing import List
from dotenv import load_dotenv

# --- System Setup ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
load_dotenv()

# --- Imports ---
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

# --- App Imports ---
from app.database.connection import SessionLocal
from app.database.repository import Repository
from app.database.models import ArticleSummary

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# --- Prompt Settings ---
SYSTEM_PROMPT = """
You are the Editor-in-Chief of a high-end technical AI newsletter. 
Your job is to take a list of raw news items and synthesize them into a cohesive, professional Daily Digest.

Guidelines:
- **Tone:** Professional, insightful, concise, and technical.
- **Structure:** 1. A Catchy Main Headline (that covers the biggest story).
    2. An "Executive Summary" (2-3 sentences tying the trends together).
    3. Categorized Sections (e.g., "Top Stories", "Research", "Industry").
    4. For each item, write a 1-sentence takeaway and provide the [Source Link].
- **Formatting:** Use clean Markdown (headers, bolding, lists).
- **Filtering:** If an item seems duplicate, merge them.
"""

# --- 1. The Output Schema ---
class DigestContent(BaseModel):
    newsletter_title: str = Field(description="A catchy subject line for today's newsletter (e.g., 'GPT-5 Rumors & New Vision Models').")
    newsletter_body: str = Field(description="The full markdown content of the newsletter.")

# --- 2. The Format Agent ---
class FormatAgent:
    def __init__(self):
        self.db = SessionLocal()
        self.repo = Repository(self.db)
        # Using a high-quality model for final synthesis
        self.llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.5)
        self.parser = PydanticOutputParser(pydantic_object=DigestContent)
        
        self.prompt = PromptTemplate(
            template=f"{SYSTEM_PROMPT}\n\n{{format_instructions}}\n\nToday's Top News (Raw Data):\n{{raw_content}}",
            input_variables=["raw_content"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        self.chain = self.prompt | self.llm | self.parser

    def get_todays_top_articles(self, min_score=50, hours=24) -> List[ArticleSummary]:
        """
        Fetches articles created in the last N hours with a score > min_score.
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Query: Filter by time AND score
        articles = self.db.query(ArticleSummary).filter(
            ArticleSummary.created_at >= cutoff_time,
            ArticleSummary.impact_score >= min_score
        ).order_by(ArticleSummary.impact_score.desc()).all()
        
        return articles

    def format_raw_input(self, articles: List[ArticleSummary]) -> str:
        """
        Turns the database objects into a text blob for the LLM to read.
        """
        raw_text = ""
        for i, art in enumerate(articles, 1):
            raw_text += f"Item {i}:\n"
            raw_text += f"- Title: {art.title}\n"
            raw_text += f"- URL: {art.source_url}\n"
            raw_text += f"- Score: {art.impact_score}\n"
            raw_text += f"- Summary: {art.summary}\n\n"
        return raw_text

    def run(self):
        print("📰 Starting Format Agent (Daily Digest)...")
        
        # 1. Fetch Data
        articles = self.get_todays_top_articles(min_score=50)
        
        if not articles:
            print("⚠️ No high-scoring articles found for today. Skipping digest.")
            return

        print(f"🔹 Found {len(articles)} high-impact articles to summarize.")
        
        # 2. Prepare Data for LLM
        raw_content = self.format_raw_input(articles)
        
        # 3. Generate Digest
        try:
            print("✍️  Synthesizing newsletter...")
            result = self.chain.invoke({"raw_content": raw_content})
            
            # 4. Save to Database
            saved = self.repo.save_daily_digest(
                title=result.newsletter_title,
                content=result.newsletter_body
            )
            
            if saved:
                print(f"✅ Daily Digest Saved: '{result.newsletter_title}'")
            else:
                print("⚠️  Digest for today already exists.")
                
        except Exception as e:
            logger.error(f"Formatting failed: {e}")

if __name__ == "__main__":
    FormatAgent().run()