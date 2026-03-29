import os
import sys
import asyncio
from typing import TypedDict
from dotenv import load_dotenv

# --- ROBUST PATH FIX ---
current_dir = os.path.dirname(os.path.abspath(__file__)) # app/agents2
parent_dir = os.path.dirname(current_dir)                # app/
sys.path.append(parent_dir)

from langgraph.graph import StateGraph, START, END

# Import Worker Agents
from agents2.scraper_agent import scrapper_agent
from agents2.cleaner_agent import cleaner_agent
from agents2.score_agent import score_agent
from agents2.summary_agent import summary_agent
from agents2.email_agent import EmailAgent

# Import The Global Profile
from agents2.profile import MY_PROFILE

load_dotenv()

# --- 1. Master State ---
class OrchestratorState(TypedDict):
    user_query: str # Now optional / background context
    top_n: int
    pipeline_status: str
    master_instruction: str  # Generated from MY_PROFILE

# --- 2. The Logic Nodes ---

async def profile_sync_node(state: OrchestratorState):
    """
    Step 0: Mission Control.
    Automatically crafts the search and analysis logic from MY_PROFILE 
    so you don't have to provide a manual query.
    """
    print("\n" + "="*50)
    print(f"🧠 BOOTING ANALYST CORE: {MY_PROFILE.name}")
    print(f"🎯 TARGETING: {', '.join(MY_PROFILE.interests[:3])}...")
    print("="*50)
    
    # Extract data from the Profile
    sources = ", ".join(MY_PROFILE.custom_sources.keys())
    interests = ", ".join(MY_PROFILE.interests)
    priority = ", ".join(MY_PROFILE.must_include)
    
    # Handle empty user query by using a default mission
    current_focus = state.get('user_query')
    if not current_focus or current_focus.strip() == "":
        current_focus = "Standard Market & Geopolitical Intelligence Gathering"

    # Build the Master Instruction (The "System Prompt" for the workers)
    instruction = f"""
    PERSONA: Senior {MY_PROFILE.preferred_depth} Analyst.
    PRIMARY FEEDS: {sources}.
    KEY TOPICS: {interests}.
    HIGH-PRIORITY SIGNALS: {priority}.
    CURRENT MISSION: {current_focus}.
    
    ACTION: Perform a deep-dive scan. Focus on cause-and-effect in {interests}.
    """
    
    return {
        "master_instruction": instruction.strip(),
        "pipeline_status": "profile_synced"
    }

async def run_scrapper_node(state: OrchestratorState):
    print("\n🛰️  STEP 1: SCRAPING (Triggering Discovery on Profile Sources)")
    await scrapper_agent.ainvoke({
        "user_query": state["master_instruction"], 
        "top_n": state["top_n"]
    })
    return {"pipeline_status": "scraped"}

async def run_cleaner_node(state: OrchestratorState):
    print("\n🧹 STEP 2: CLEANING & FACT EXTRACTION")
    await cleaner_agent.ainvoke({"raw_articles": []})
    return {"pipeline_status": "cleaned"}

async def run_scorer_node(state: OrchestratorState):
    print("\n🎯 STEP 3: PERSONALIZED SCORING")
    await score_agent.ainvoke({"articles_to_score": []})
    return {"pipeline_status": "scored"}

async def run_summarizer_node(state: OrchestratorState):
    print("\n✍️  STEP 4: NARRATIVE SYNTHESIS")
    await summary_agent.ainvoke({"pending_summaries": []})
    return {"pipeline_status": "summarized"}

async def run_email_node(state: OrchestratorState):
    print("\n📧 STEP 5: NEWSLETTER DELIVERY")
    EmailAgent().run()
    return {"pipeline_status": "completed"}

# --- 3. Graph Construction ---



builder = StateGraph(OrchestratorState)

builder.add_node("sync", profile_sync_node)
builder.add_node("scrapper", run_scrapper_node)
builder.add_node("cleaner", run_cleaner_node)
builder.add_node("scorer", run_scorer_node)
builder.add_node("summarizer", run_summarizer_node)
builder.add_node("emailer", run_email_node)

builder.add_edge(START, "sync")
builder.add_edge("sync", "scrapper")
builder.add_edge("scrapper", "cleaner")
builder.add_edge("cleaner", "scorer")
builder.add_edge("scorer", "summarizer")
builder.add_edge("summarizer", "emailer")
builder.add_edge("emailer", END)

orchestrator = builder.compile()

# --- 4. Execution ---

if __name__ == "__main__":
    async def main():
        # HANDS-FREE: No query required. 
        # The 'sync' node builds the prompt from your profile automatically.
        inputs = {
            "user_query": "", 
            "top_n": 1 
        }
        
        print("🚀 STARTING AUTOMATED NEWS PIPELINE...")
        await orchestrator.ainvoke(inputs)
        print("\n✨ PIPELINE COMPLETE: Your Analyst Digest is ready.")

    asyncio.run(main())