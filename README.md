import os
import sys
import asyncio
from typing import TypedDict
from dotenv import load_dotenv

# --- ROBUST PATH FIX ---
# This ensures that no matter where you run the script from, 
# it finds the 'app' directory as the root.
current_dir = os.path.dirname(os.path.abspath(__file__)) # app/agents2
parent_dir = os.path.dirname(current_dir)                # app/
sys.path.append(parent_dir)

from langgraph.graph import StateGraph, START, END

# Import agents using the parent directory context
try:
    from agents2.scraper_agent import scrapper_agent
    from agents2.cleaner_agent import cleaner_agent
    from agents2.score_agent import score_agent
    from agents2.summary_agent import summary_agent
    from agents2.email_agent import EmailAgent
except ImportError as e:
    print(f"❌ Import Error: {e}")
    # Fallback for direct imports if pathing is strict
    from scrapper_agent import scrapper_agent
    from cleaner_agent import cleaner_agent
    from score_agent import score_agent
    from summary_agent import summary_agent
    from email_agent import EmailAgent

load_dotenv()

class OrchestratorState(TypedDict):
    user_query: str
    top_n: int
    pipeline_status: str

# Nodes remain the same as your provided code
async def run_scrapper_node(state: OrchestratorState):
    print("\n--- 🛰️ STEP 1: SCRAPING ---")
    await scrapper_agent.ainvoke({"user_query": state["user_query"], "top_n": state["top_n"]})
    return {"pipeline_status": "scraped"}

async def run_cleaner_node(state: OrchestratorState):
    print("\n--- 🧹 STEP 2: CLEANING & EXTRACTION ---")
    await cleaner_agent.ainvoke({"raw_articles": []})
    return {"pipeline_status": "cleaned"}

async def run_scorer_node(state: OrchestratorState):
    print("\n--- 🎯 STEP 3: PERSONALIZED SCORING ---")
    await score_agent.ainvoke({"articles_to_score": []})
    return {"pipeline_status": "scored"}

async def run_summarizer_node(state: OrchestratorState):
    print("\n--- ✍️ STEP 4: NARRATIVE SYNTHESIS ---")
    await summary_agent.ainvoke({"pending_summaries": []})
    return {"pipeline_status": "summarized"}

async def run_email_node(state: OrchestratorState):
    print("\n--- 📧 STEP 5: NEWSLETTER DELIVERY ---")
    EmailAgent().run()
    return {"pipeline_status": "completed"}

builder = StateGraph(OrchestratorState)
builder.add_node("scrapper", run_scrapper_node)
builder.add_node("cleaner", run_cleaner_node)
builder.add_node("scorer", run_scorer_node)
builder.add_node("summarizer", run_summarizer_node)
builder.add_node("emailer", run_email_node)

builder.add_edge(START, "scrapper")
builder.add_edge("scrapper", "cleaner")
builder.add_edge("cleaner", "scorer")
builder.add_edge("scorer", "summarizer")
builder.add_edge("summarizer", "emailer")
builder.add_edge("emailer", END)

orchestrator = builder.compile()

if __name__ == "__main__":
    async def main():
        inputs = {"user_query": "", "top_n": 1}
        await orchestrator.ainvoke(inputs)
    asyncio.run(main())