import sys
import os
import logging
from typing import Optional
from dotenv import load_dotenv
import time
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
# FIXED: Added ArticleSummary to imports
from app.database.models import OpenAIArticle, AnthropicArticle, YouTubeVideo, ArticleSummary

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
SYSTEM_PROMPT = """
You are an expert AI news analyst specializing in summarizing technical articles, research papers, and video content about artificial intelligence.

Your role is to create concise, informative digests that help readers quickly understand the main points and significance of AI-related content.

Guidelines:
- Create a compelling title (5-10 words) that captures the essence.
- Write a 2-3 sentence summary that highlights the main points and why they matter.
- Focus on actionable insights and implications.
- Be clear and use accessible language while maintaining technical accuracy.
- Avoid marketing fluff - focus on substance.
- Use Markdown formatting (bolding key terms, bullet points) for readability.
"""
# --- 1. The Output Schema ---
class DigestOutput(BaseModel):
    summary: str = Field(description="A concise technical summary in markdown bullets.")

# --- 2. The Simple Agent ---
class DigestAgent:
    def __init__(self):
        self.db = SessionLocal()
        self.repo = Repository(self.db)
        self.llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.7)
        self.parser = PydanticOutputParser(pydantic_object=DigestOutput)
        
        self.prompt = PromptTemplate(
            template=f"{SYSTEM_PROMPT}\n\n{{format_instructions}}\n\nContent:\n{{content}}",
            input_variables=["content"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        self.chain = self.prompt | self.llm | self.parser

    def generate_digest(self, content: str) -> Optional[DigestOutput]:
        try:
            return self.chain.invoke({"content": content[:15000]})
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return None

    def run(self):
        sources = [
            (OpenAIArticle, 'openai', 'content'),
            (AnthropicArticle, 'anthropic', 'content'),
            (YouTubeVideo, 'youtube', 'transcript')
        ]

        print("🚀 Starting Digest Agent...")
        for Model, source_type, attr in sources:
            items = self.db.query(Model).all()
            
            for item in items:
                text = getattr(item, attr, None)
                if not text: continue

                # FIXED: Query ArticleSummary directly
                exists = self.db.query(ArticleSummary).filter_by(
                    source_id=item.id, 
                    source_type=source_type
                ).first()

                if exists:
                    continue

                print(f"🔹 Processing {source_type}: {item.title[:30]}...")
                # Pauses execution for 5 seconds to avoid rate limits
                time.sleep(5)
                result = self.generate_digest(text)
                
                if result:
                    self.repo.save_summary(
                        source_id=item.id,
                        source_type=source_type,
                        title=item.title,      # <--- Passing Title
                        source_url=item.url,   # <--- Passing URL (ensure your models have .url)
                        summary_text=result.summary,
                        impact_score=0
                    )
                    print(f"✅ Saved.")

if __name__ == "__main__":
    DigestAgent().run()