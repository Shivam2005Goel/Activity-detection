from datetime import date
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Filters(BaseModel):
    date_start: Optional[date] = None
    date_end: Optional[date] = None
    country: Optional[str] = None
    transaction_type: Optional[str] = None
    customer_segment: Optional[str] = None
    amount_threshold: Optional[float] = None
    min_transaction_count: Optional[int] = None


class Intent(BaseModel):
    intent_type: Literal["pattern_search", "aggregation_query", "entity_lookup", "broad_exploration"]
    target_pattern: Literal["structuring", "smurfing", "layering", "rapid_cashout", "none"] = "none"
    filters: Filters = Field(default_factory=Filters)
    entity_id: Optional[str] = None
    requires_full_eda: bool = False
    requires_ml_detection: bool = False
    confidence: float = 1.0  # 0-1, how confident the parser is in this extraction


class FlaggedItem(BaseModel):
    customer_id: str
    risk_score: float          # 0-100
    risk_level: Literal["Low", "Medium", "High", "Critical"]
    confidence: float          # 0-100
    trust_score: float         # 0-100
    pattern_matched: Optional[str] = None
    explanation: str
    evidence_transaction_ids: List[str] = Field(default_factory=list)
    recommended_action: Literal["monitor", "review", "report"]
    consensus: Dict[str, Any] = Field(default_factory=dict)            # {"rule_engine": "...", "ml_model": "...", "agreement": "..."}


class ExecutionSummary(BaseModel):
    agents_used: List[str] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    tools_skipped: List[str] = Field(default_factory=list)
    planning_type: str = "dynamic_rule_based"
    verification_status: Literal["Passed", "Failed", "Needs Review"] = "Passed"
    bias_warning: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    query: str
    detected_intent: Intent
    results: List[FlaggedItem] = Field(default_factory=list)
    execution_summary: ExecutionSummary
    charts: List[str] = Field(default_factory=list)      # file paths or base64 references
    error: Optional[str] = None
