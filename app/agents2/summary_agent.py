import os
import sys
import asyncio
from typing import List, TypedDict, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END

from app.database.connection import SessionLocal
from app.database.models import AggregatedSummary, ScrapedArticle
from agents2.profile import MY_PROFILE

load_dotenv()

# --- 1. Models ---
class ContextSummary(BaseModel):
    brief_context: str = Field(description="A condensed version of the raw article content, focusing on background info.")

class NarrativeSummary(BaseModel):
    narrative: str = Field(description="The final professional 3-sentence narrative summary.")

# --- 2. State ---
class SummaryState(TypedDict):
    pending_summaries: List[dict]
    current_context_summary: Optional[str]

# --- 3. Nodes ---

async def fetch_high_score_facts(state: SummaryState):
    """Fetch articles scored >= 50 that still have bullet-point summaries."""
    session = SessionLocal()
    results = session.query(AggregatedSummary, ScrapedArticle).\
        join(ScrapedArticle, AggregatedSummary.source_link == ScrapedArticle.source_link).\
        filter(AggregatedSummary.impact_score >= 50).\
        filter(AggregatedSummary.summary.like("•%")).limit(5).all()
    
    data = []
    for agg, raw in results:
        data.append({
            "id": agg.id,
            "title": agg.article_name,
            "facts": agg.summary,
            "raw_content": raw.full_content 
        })
    session.close()
    print(f"📥 Found {len(data)} high-priority articles for narrative synthesis.")
    return {"pending_summaries": data}

async def stage_1_context_node(state: SummaryState):
    """Stage 1: Summarize messy raw data with Rate Limit Protection."""
    # ⏱️ SLEEP: Replacing RetryPolicy with a simple sleep
    await asyncio.sleep(5) 

    article = state["pending_summaries"][0]
    llm_struct = llm.with_structured_output(ContextSummary)
    
    prompt = f"""
    You are a Content Distiller. Summarize the following messy article content into a 
    dense 200-word background summary. Ignore ads, headers, and navigation.
    
    TITLE: {article['title']}
    MESSY CONTENT: {article['raw_content'][:15000]}
    """
    
    print(f"🔬 Stage 1: Distilling context for '{article['title'][:30]}...'")
    res = await llm_struct.ainvoke(prompt)
    return {"current_context_summary": res.brief_context}

async def stage_2_synthesis_node(state: SummaryState):
    """Stage 2: Final Synthesis with Rate Limit Protection."""
    # ⏱️ SLEEP: Replacing RetryPolicy with a simple sleep
    await asyncio.sleep(5) 

    article = state["pending_summaries"][0]
    context = state["current_context_summary"]
    llm_struct = llm.with_structured_output(NarrativeSummary)
    
    prompt = f"""
    You are a Senior Editor for {MY_PROFILE.name}. 
    Create a final 3-sentence narrative by combining the 'Verified Facts' and the 'Context Summary'.
    
    VERIFIED FACTS:
    {article['facts']}
    
    CONTEXT SUMMARY:
    {context}
    
    STYLE: {MY_PROFILE.preferred_depth} narrative. 
    Focus on the "So what?" for a {MY_PROFILE.bio}.
    """
    
    print(f"✍️ Stage 2: Synthesizing final narrative...")
    res = await llm_struct.ainvoke(prompt)
    
    session = SessionLocal()
    db_item = session.query(AggregatedSummary).filter(AggregatedSummary.id == article['id']).first()
    if db_item:
        db_item.summary = res.narrative
        session.commit()
    session.close()
    
    return {"pending_summaries": state["pending_summaries"][1:]}

# --- 4. Graph Construction ---

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)

builder = StateGraph(SummaryState)

builder.add_node("fetch", fetch_high_score_facts)
# Simple nodes without retry_policy argument
builder.add_node("distill", stage_1_context_node)
builder.add_node("synthesize", stage_2_synthesis_node)

builder.add_edge(START, "fetch")
builder.add_edge("distill", "synthesize")

builder.add_conditional_edges(
    "fetch", 
    lambda s: "distill" if s["pending_summaries"] else END
)
builder.add_conditional_edges(
    "synthesize", 
    lambda s: "distill" if s["pending_summaries"] else END
)

summary_agent = builder.compile()

if __name__ == "__main__":
    async def run():
        await summary_agent.ainvoke({"pending_summaries": []})
    asyncio.run(run())