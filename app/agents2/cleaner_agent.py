import os
import sys
import asyncio
import time
from typing import Annotated, List, TypedDict, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
# --- NEW IMPORT ---
from langgraph.pregel.retry import RetryPolicy

from app.database.connection import SessionLocal
from app.database.repository import Repository

load_dotenv()

# --- 1. Models (Unchanged) ---
class ExtractedFacts(BaseModel):
    facts: List[str] = Field(description="A list of objective, verifiable news facts extracted from the text.")
    is_junk: bool = Field(description="True if the content is an ad, login wall, or contains no news.")

class ValidationResult(BaseModel):
    is_hallucinated: bool = Field(description="True if the facts contain info not found in the raw text.")
    cleaned_facts: List[str] = Field(description="The final verified list of facts.")

# --- 2. State ---
class CleanerState(TypedDict):
    raw_articles: List[dict]
    current_raw_text: str
    extracted_facts: List[str]
    is_junk: bool
    processed_count: int

# --- 3. Nodes ---

async def fetch_raw_node(state: CleanerState):
    session = SessionLocal()
    repo = Repository(session)
    articles = repo.get_unprocessed_scraped_articles(limit=5)
    session.close()
    
    raw_list = []
    for a in articles:
        raw_list.append({
            "id": a.id,
            "title": a.article_name,
            "content": a.full_content,
            "link": a.source_link,
            "date": a.published_date
        })
    print(f"📦 Fetched {len(raw_list)} raw articles for cleaning.")
    return {"raw_articles": raw_list, "processed_count": 0}

async def extraction_node(state: CleanerState):
    """Node 1: Extract core facts with Rate Limit Protection."""
    # ⏱️ PAUSE: Give the API a breather before the request
    await asyncio.sleep(2) 
    
    article = state["raw_articles"][0]
    llm_struct = llm.with_structured_output(ExtractedFacts)
    
    prompt = f"""
    You are a Data Extraction Expert. Strip all HTML noise, ads, and footers.
    Extract only the verifiable news facts from this content.
    
    TITLE: {article['title']}
    CONTENT: {article['content'][:12000]}
    """
    
    print(f"🧹 Extracting facts: {article['title'][:40]}...")
    res = await llm_struct.ainvoke(prompt)
    return {"extracted_facts": res.facts, "is_junk": res.is_junk, "current_raw_text": article['content'][:5000]}

async def validation_node(state: CleanerState):
    """Node 2: Validate facts with Rate Limit Protection."""
    if state["is_junk"]:
        return {"extracted_facts": []}

    # ⏱️ PAUSE: Rate Limit protection
    await asyncio.sleep(2)

    llm_struct = llm.with_structured_output(ValidationResult)
    
    prompt = f"""
    You are a Fact Checker. Compare these 'Extracted Facts' against the 'Source Text'.
    Remove any fact that is not explicitly supported by the Source Text.
    
    SOURCE TEXT: {state['current_raw_text']}
    EXTRACTED FACTS: {state['extracted_facts']}
    """
    
    print(f"⚖️ Validating facts for accuracy...")
    res = await llm_struct.ainvoke(prompt)
    return {"extracted_facts": res.cleaned_facts}

def save_cleaned_data_node(state: CleanerState):
    article = state["raw_articles"][0]
    session = SessionLocal()
    repo = Repository(session)
    
    cleaned_content = "\n".join([f"• {f}" for f in state["extracted_facts"]]) if not state["is_junk"] else "Junk/No Content"

    class CleanedData:
        article_name = article['title']
        source_link = article['link']
        published_date = article['date']
        summary = cleaned_content 
        impact_score = 0
        explanation = "Cleaned by Extraction Agent"

    repo.save_aggregated_summary(CleanedData())
    session.close()
    
    print(f"✅ Data Cleaned & Saved: {article['title'][:40]}")
    return {"raw_articles": state["raw_articles"][1:], "processed_count": state["processed_count"] + 1}

# --- 4. Graph Construction ---

# 🛡️ DEFINE RETRY POLICY: Handle 429s automatically
# wait_min: Initial wait time
# backoff_factor: Multiply wait time on subsequent failures (5s, 10s, 20s...)
rate_limit_retry = RetryPolicy(
    max_attempts=3,
    wait_min=5.0,
    backoff_factor=2.0
)

def router(state: CleanerState):
    if len(state["raw_articles"]) > 0:
        return "extract"
    return END

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

workflow = StateGraph(CleanerState)

# Add nodes with the retry policy attached
workflow.add_node("fetch", fetch_raw_node)
workflow.add_node("extract", extraction_node, retry=rate_limit_retry)
workflow.add_node("validate", validation_node, retry=rate_limit_retry)
workflow.add_node("save", save_cleaned_data_node)

workflow.add_edge(START, "fetch")
workflow.add_edge("fetch", "extract")
workflow.add_edge("extract", "validate")
workflow.add_edge("validate", "save")

workflow.add_conditional_edges("save", router, {"extract": "extract", END: END})

cleaner_agent = workflow.compile()

if __name__ == "__main__":
    async def run():
        await cleaner_agent.ainvoke({"raw_articles": []})
    asyncio.run(run())