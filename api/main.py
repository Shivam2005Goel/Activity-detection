import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import json

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
    session_id: Optional[str] = None

class FeedbackRequest(BaseModel):
    customer_id: str
    feedback: str # "True Positive" or "False Positive"
    session_id: Optional[str] = None

# Simple in-memory session storage for conversational memory
SESSION_MEMORY: Dict[str, List[Dict[str, str]]] = {}


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

    session_id = req.session_id or "default"
    if session_id not in SESSION_MEMORY:
        SESSION_MEMORY[session_id] = []
        
    history = SESSION_MEMORY[session_id]

    try:
        # Pass history to run_agent
        response = run_agent(req.query.strip(), history=history)
        
        # Update history
        history.append({"role": "user", "content": req.query.strip()})
        history.append({"role": "agent", "content": response.summary_text or "Processed."})
        
        # Keep only last 10 turns to avoid context overflow
        SESSION_MEMORY[session_id] = history[-10:]
        
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

@app.post("/agent/feedback")
def submit_feedback(req: FeedbackRequest):
    """
    Endpoint for HITL feedback (True Positive / False Positive).
    Generates a SAR report on True Positive.
    """
    from datetime import datetime
    feedback_file = Path(BASE_DIR) / "feedback_log.jsonl"
    feedback_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "customer_id": req.customer_id,
        "feedback": req.feedback,
        "session_id": req.session_id
    }
    
    try:
        with open(feedback_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_entry) + "\n")
        log_event("HITL_FEEDBACK_RECEIVED", feedback_entry)
        
        # If True Positive, generate SAR report
        if req.feedback == "True Positive":
            sars_dir = Path(BASE_DIR) / "sars"
            sars_dir.mkdir(exist_ok=True)
            sar_file = sars_dir / f"SAR_{req.customer_id}_{int(datetime.utcnow().timestamp())}.md"
            
            sar_content = f"""# Suspicious Activity Report (SAR)

**Date of Report:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
**Subject:** Customer {req.customer_id}
**Reported By:** Automated Agentic AML System (Confirmed via HITL Analyst Feedback)

## 1. Subject Information
- **Customer ID:** {req.customer_id}

## 2. Suspicious Activity Details
- **Reason for Filing:** This customer was automatically flagged by the ML anomaly detection and/or rule engine, and subsequently confirmed as highly suspicious by an internal investigator.
- **Session Reference ID:** {req.session_id or 'N/A'}

## 3. Recommended Actions
- Freeze transactions pending further manual review.
- Request enhanced due diligence (EDD) documents from the customer.

---
*This is an automatically generated SAR summary produced by the internal AML Agent. Please attach supporting transaction logs before submitting to regulatory bodies.*
"""
            with open(sar_file, "w", encoding="utf-8") as sf:
                sf.write(sar_content)
            log_event("SAR_GENERATED", {"customer_id": req.customer_id, "file": str(sar_file)})
            return {"status": "success", "message": "Feedback recorded. SAR generated."}
            
        return {"status": "success", "message": "Feedback recorded."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



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
