import os
import sys
import asyncio
from typing import List, TypedDict
from pydantic import BaseModel, Field
from sqlalchemy import desc
from dotenv import load_dotenv

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import StateGraph, START, END

from app.database.connection import SessionLocal
from app.database.models import ScrapedArticle, AggregatedSummary
from app.database.repository import Repository

load_dotenv()

# --- 1. Models ---
class ExtractedFacts(BaseModel):
    facts: List[str] = Field(description="A list of objective news facts.")
    is_junk: bool = Field(description="True if content is an ad or junk.")

class ValidationResult(BaseModel):
    cleaned_facts: List[str] = Field(description="Verified list of facts.")

w

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
fact_parser = PydanticOutputParser(pydantic_object=ExtractedFacts)
val_parser = PydanticOutputParser(pydantic_object=ValidationResult)

# --- 3. Nodes ---

async def fetch_recent_raw_node(state: CleanerState):
    """
    FIXED: Uses a Join to find articles that haven't been summarized yet.
    Does NOT require the 'is_processed' column.
    """
    session = SessionLocal()
    
    # Logic: Get ScrapedArticles that don't exist in AggregatedSummary based on link
    articles = session.query(ScrapedArticle).outerjoin(
        AggregatedSummary, ScrapedArticle.source_link == AggregatedSummary.source_link
    ).filter(
        AggregatedSummary.id == None  # This means no summary exists yet
    ).order_by(desc(ScrapedArticle.created_at)).limit(10).all()
    
    raw_list = [{"id": a.id, "title": a.article_name, "content": a.full_content, 
                 "link": a.source_link, "date": a.published_date} for a in articles]
    
    session.close()
    print(f"📦 Fetched {len(raw_list)} NEW raw articles (via Left Join logic).")
    return {"raw_articles": raw_list, "processed_count": 0}

async def extraction_node(state: CleanerState):
    await asyncio.sleep(2) 
    article = state["raw_articles"][0]
    
    prompt = PromptTemplate(
        template="Extract news facts from: {title}\n\nContent: {content}\n\n{format_instructions}",
        input_variables=["title", "content"],
        partial_variables={"format_instructions": fact_parser.get_format_instructions()}
    )
    
    chain = prompt | llm | fact_parser
    print(f"🧹 Cleaning: {article['title'][:40]}...")
    
    try:
        res = await chain.ainvoke({"title": article['title'], "content": article['content'][:8000]})
        return {"extracted_facts": res.facts, "is_junk": res.is_junk, "current_raw_text": article['content'][:4000]}
    except Exception as e:
        print(f"❌ API Error: {e}")
        return {"extracted_facts": [], "is_junk": True}

async def validation_node(state: CleanerState):
    if state["is_junk"] or not state["extracted_facts"]: return {"extracted_facts": []}
    await asyncio.sleep(2)

    prompt = PromptTemplate(
        template="Verify these facts: {facts}\nSource: {source}\n\n{format_instructions}",
        input_variables=["facts", "source"],
        partial_variables={"format_instructions": val_parser.get_format_instructions()}
    )
    
    chain = prompt | llm | val_parser
    print(f"⚖️ Validating...")
    try:
        res = await chain.ainvoke({"facts": state['extracted_facts'], "source": state['current_raw_text']})
        return {"extracted_facts": res.cleaned_facts}
    except:
        return {"extracted_facts": state['extracted_facts']}

def save_cleaned_data_node(state: CleanerState):
    article = state["raw_articles"][0]
    session = SessionLocal()
    repo = Repository(session)
    
    # We save as 'AggregatedSummary' which our 'fetch' logic uses to know it's done.
    if not state["is_junk"] and state["extracted_facts"]:
        cleaned_content = "\n".join([f"• {f}" for f in state["extracted_facts"]])

        # Using your existing class structure for save_aggregated_summary
        class CleanedData:
            article_name = article['title']
            source_link = article['link']
            published_date = article['date']
            summary = cleaned_content 
            impact_score = 0
            explanation = "Cleaned via Pydantic Parser"

        repo.save_aggregated_summary(CleanedData())
        print(f"✅ Saved & Linked: {article['title'][:40]}")
    else:
        # Even if it's junk, we should ideally create a record or mark it 
        # to prevent re-scraping the same junk over and over.
        print(f"🗑️ Junk ignored: {article['title'][:40]}")

    session.close()
    return {"raw_articles": state["raw_articles"][1:], "processed_count": state["processed_count"] + 1}

# --- 4. Graph Construction ---

def router(state: CleanerState):
    return "extract" if state["raw_articles"] else END

builder = StateGraph(CleanerState)
builder.add_node("fetch", fetch_recent_raw_node)
builder.add_node("extract", extraction_node)
builder.add_node("validate", validation_node)
builder.add_node("save", save_cleaned_data_node)

builder.add_edge(START, "fetch")
builder.add_edge("fetch", "extract")
builder.add_edge("extract", "validate")
builder.add_edge("validate", "save")
builder.add_conditional_edges("save", router)

cleaner_agent = builder.compile()

if __name__ == "__main__":
    asyncio.run(cleaner_agent.ainvoke({"raw_articles": []}))