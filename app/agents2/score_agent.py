import os
import sys
import asyncio
from typing import List, TypedDict
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END

from app.database.connection import SessionLocal
from app.database.models import AggregatedSummary
from agents2.profile import MY_PROFILE 

load_dotenv()

class ScoreResult(BaseModel):
    impact_score: int = Field(description="0-100 score.")
    explanation: str = Field(description="Why this score was given based on user interests.")

class ScoreState(TypedDict):
    articles_to_score: List[dict]
    processed_count: int

# --- 1. Nodes ---

async def fetch_unscored_node(state: ScoreState):
    """Fetch rows that were processed by the Cleaner but not yet scored."""
    session = SessionLocal()
    unscored = session.query(AggregatedSummary).filter(AggregatedSummary.impact_score == 0).limit(10).all()
    
    articles = [{"id": a.id, "title": a.article_name, "facts": a.summary} for a in unscored]
    session.close()
    print(f"🎯 Fetched {len(articles)} articles for scoring.")
    return {"articles_to_score": articles, "processed_count": 0}

async def scoring_node(state: ScoreState):
    """Evaluate importance based on MY_PROFILE with Rate Limit Protection."""
    # ⏱️ SLEEP: Replacing RetryPolicy with a simple sleep
    await asyncio.sleep(5) 

    article = state["articles_to_score"][0]
    llm_struct = llm.with_structured_output(ScoreResult)
    
    prompt = f"""
    You are a Personalized News Curator for {MY_PROFILE.name}.
    
    USER BIO: {MY_PROFILE.bio}
    PRIMARY INTERESTS: {", ".join(MY_PROFILE.interests)}
    MUST INCLUDE (High Priority): {", ".join(MY_PROFILE.must_include)}
    IGNORE THESE TOPICS (Score 0): {", ".join(MY_PROFILE.ignore_topics)}
    PREFERRED DEPTH: {MY_PROFILE.preferred_depth}

    NEWS ARTICLE TO EVALUATE:
    TITLE: {article['title']}
    CLEANED FACTS: {article['facts']}
    
    SCORING RULES:
    1. If the article is about {", ".join(MY_PROFILE.ignore_topics)}, score is 0.
    2. If it mentions {", ".join(MY_PROFILE.must_include)}, increase score significantly (85+).
    3. Evaluate if the depth is '{MY_PROFILE.preferred_depth}'.
    """
    
    print(f"⚖️ Personalized Scoring for {MY_PROFILE.name}: {article['title'][:40]}...")
    
    try:
        result = await llm_struct.ainvoke(prompt)
        
        # Update DB
        session = SessionLocal()
        db_article = session.query(AggregatedSummary).filter(AggregatedSummary.id == article['id']).first()
        if db_article:
            db_article.impact_score = result.impact_score
            db_article.relevance_explanation = result.explanation
            session.commit()
        session.close()
    except Exception as e:
        print(f"⚠️ Scoring Error: {e}. Waiting 10s...")
        await asyncio.sleep(10)
    
    return {
        "articles_to_score": state["articles_to_score"][1:], 
        "processed_count": state["processed_count"] + 1
    }

# --- 2. Graph Construction ---

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

builder = StateGraph(ScoreState)
builder.add_node("fetch", fetch_unscored_node)
# Simple node without retry_policy argument
builder.add_node("score", scoring_node)

builder.add_edge(START, "fetch")
builder.add_conditional_edges("fetch", lambda s: "score" if s["articles_to_score"] else END)
builder.add_conditional_edges("score", lambda s: "score" if s["articles_to_score"] else END)

score_agent = builder.compile()

if __name__ == "__main__":
    async def run():
        await score_agent.ainvoke({"articles_to_score": [], "processed_count": 0})
    asyncio.run(run())