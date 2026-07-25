import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config
from schemas import AgentResponse, Intent, ExecutionSummary
from agents.orchestrator import run_agent
from safety.audit_logger import get_recent_audit_logs, log_event

app = FastAPI(
    title="Agentic AML Suspicious Activity Detection API",
    description="Dynamic Multi-Agent System for Anti-Money Laundering Detection",
    version="1.0.0"
)

# Enable CORS for local Streamlit access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AML Agentic System",
        "version": "1.0.0"
    }


@app.get("/audit-log")
def fetch_audit_logs(limit: int = 50):
    """
    Returns recent entries from audit_log.jsonl for dashboard display.
    """
    logs = get_recent_audit_logs(limit=limit)
    return {"status": "success", "count": len(logs), "logs": logs}


@app.post("/agent/query", response_model=AgentResponse)
def execute_query(req: QueryRequest):
    """
    Main API endpoint for parsing and executing natural language AML queries.
    """
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    try:
        response = run_agent(req.query.strip())
        return response
    except Exception as e:
        log_event("API_UNHANDLED_EXCEPTION", {"query": req.query, "error": str(e)})
        # Never return raw 500 stack trace — return structured AgentResponse error
        return AgentResponse(
            query=req.query,
            detected_intent=Intent(intent_type="broad_exploration", confidence=0.0),
            results=[],
            execution_summary=ExecutionSummary(
                agents_used=["API Error Handler"],
                tools_used=[],
                tools_skipped=[],
                verification_status="Failed"
            ),
            error=f"Internal Processing Error: {str(e)}"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "verification_status": "Failed"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
