import os
import sys
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from agents2.orchestrator import orchestrator
from agents2.profile import UserProfile

app = FastAPI(title="Agents2 News Engine")

class PipelineRequest(BaseModel):
    name: str
    email: str
    interests: List[str]
    must_include: List[str]
    query: str

async def run_pipeline(data: PipelineRequest):
    print(f"🚀 Background Pipeline Started for {data.name}...")
    # Trigger the orchestrator
    # Note: In a production app, you'd override the MY_PROFILE 
    # dynamicly, but for now, we trigger the workflow.
    await orchestrator.ainvoke({
        "user_query": data.query,
        "top_n": 2
    })

@app.post("/trigger-digest")
async def trigger_digest(request: PipelineRequest, background_tasks: BackgroundTasks):
    # We run this as a background task so the UI doesn't time out
    background_tasks.add_task(run_pipeline, request)
    return {"status": "success", "message": "Pipeline triggered in background. You will receive an email shortly!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)