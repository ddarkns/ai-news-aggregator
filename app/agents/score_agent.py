import sys
import os
import logging
import time
from typing import Optional
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
from profiles import PROFILES as profiles
# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# --- USER PROFILE & SYSTEM PROMPT ---
# Modify this to change how the AI scores your content
USER_PROFILE = """
You are a content curator for a Senior AI Engineer. 
They are interested in:
- Technical implementation details and code.
- New state-of-the-art (SOTA) model architectures.
- Major industry shifts (e.g., OpenAI releasing a new model).

They are NOT interested in:
- Generic "AI will change the world" fluff.
- Basic "What is AI?" tutorials.
- Marketing hype without technical substance.
"""

SCORING_INSTRUCTIONS = """
Analyze the provided article summary based on the User Profile.
Assign an 'impact_score' from 0 to 100:
- 0-20: Irrelevant or fluff.
- 21-50: Mildly interesting but low priority.
- 51-80: Good technical read, relevant.
- 81-100: Must-read, critical update, or high-value tutorial.

Return the result strictly in JSON format matching the schema.
"""

# --- 1. The Output Schema ---
class ScoreOutput(BaseModel):
    title: str = Field(description="The title of the article being scored.")
    impact_score: int = Field(description="The relevance score from 0-100.")
    reasoning: str = Field(description="A very brief (1 sentence) reason for the score.")

# --- 2. The Score Agent ---
class ScoreAgent:
    def __init__(self):
        self.db = SessionLocal()
        self.repo = Repository(self.db)
        
        # Using a smaller/faster model for scoring if available, or stay with the reliable one
        self.llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.1) 
        self.parser = PydanticOutputParser(pydantic_object=ScoreOutput)
        
        self.prompt = PromptTemplate(
            template=f"{USER_PROFILE}\n{SCORING_INSTRUCTIONS}\n\n{{format_instructions}}\n\nArticle Title: {{title}}\nArticle Summary:\n{{summary}}",
            input_variables=["title", "summary"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()}
        )
        self.chain = self.prompt | self.llm | self.parser

    def calculate_score(self, title: str, summary: str) -> Optional[ScoreOutput]:
        try:
            return self.chain.invoke({"title": title, "summary": summary})
        except Exception as e:
            logger.error(f"Scoring failed for '{title}': {e}")
            return None

    def run(self):
        print("🎯 Starting Score Agent...")
        
        # 1. Fetch all summaries where score is 0 (unscored)
        # Using filter(ArticleSummary.impact_score == 0)
        unscored_items = self.db.query(ArticleSummary).filter(ArticleSummary.impact_score == 0).all()
        
        count = len(unscored_items)
        print(f"Found {count} articles to score.")

        for item in unscored_items:
            print(f"🔹 Scoring: {item.title[:40]}...")
            
            # Rate limit buffer
            time.sleep(2) 
            
            # 2. Ask LLM for score
            result = self.calculate_score(item.title, item.summary)
            
            if result:
                # 3. Update Database
                self.repo.update_impact_score(item.id, result.impact_score)
                print(f"   ✅ Score: {result.impact_score}/100 | Reason: {result.reasoning}")
            else:
                print("   ❌ Failed to score.")

if __name__ == "__main__":
    ScoreAgent().run()