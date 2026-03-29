import os
import sys
import asyncio

# --- 1. THE ABSOLUTE WINDOWS FIX (CRITICAL) ---
# This must be at the very top, before any other imports.
# Uvicorn on Windows defaults to ProactorEventLoop which lacks subprocess support.
if sys.platform == 'win32':
    try:
        # Check if it's already set to avoid recursion/errors
        if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsSelectorEventLoopPolicy):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

# --- 2. PATH CONFIGURATION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- 3. IMPORTS ---
import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from sqlalchemy import func
from contextlib import asynccontextmanager

# Local Imports
from app.agents2.orchestrator import orchestrator
from app.agents2.profile import ProfileGenerator
from app.database.connection import SessionLocal
from app.database.models import AggregatedSummary, DailyDigest

# --- 4. LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Secondary check inside the running loop
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    yield

app = FastAPI(
    title="AI News Analyst API",
    version="1.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 5. SCHEMAS ---
class PipelineRequest(BaseModel):
    user_query: Optional[str] = ""
    top_n: Optional[int] = 1

class ProfileSuggestRequest(BaseModel):
    name: str
    bio: str

# --- 6. ENDPOINTS ---

@app.post("/run-pipeline", status_code=202)
async def trigger_pipeline(request: PipelineRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(
        orchestrator.ainvoke, 
        {"user_query": request.user_query, "top_n": request.top_n}
    )
    return {"status": "success", "message": "Pipeline triggered."}

@app.get("/news/today")
def get_today_articles():
    session = SessionLocal()
    try:
        return session.query(AggregatedSummary).filter(
            func.date(AggregatedSummary.created_at) == date.today()
        ).order_by(AggregatedSummary.impact_score.desc()).all()
    finally:
        session.close()

@app.get("/news/digest")
def get_daily_html():
    session = SessionLocal()
    try:
        digest = session.query(DailyDigest).filter(
            func.date(DailyDigest.date) == date.today()
        ).first()
        return {"html": digest.content if digest else "<h3>Preparing...</h3>", "ready": bool(digest)}
    finally:
        session.close()

@app.post("/profile/suggest")
async def suggest_profile(request: ProfileSuggestRequest):
    generator = ProfileGenerator()
    suggested = await generator.generate_from_bio(request.name, request.bio)
    return suggested.dict()

# --- 7. STARTUP LOGIC ---
if __name__ == "__main__":
    # ON WINDOWS: Try running WITHOUT reload=True first to verify the fix.
    # reload=True spawns child processes that often ignore the parent's loop policy.
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)