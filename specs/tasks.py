from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class Topic(BaseModel):
    """
    Topic Definition [cite: 222, 267]
    The semantic coloring of the token.
    """
    id: str
    description: str
    weight: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0.0-1.0)")

class Token(BaseModel):
    """
    TB-CSPN Token Implementation [cite: 315]
    Combines Data Payload (for Validator) with Semantic Context (for CPN).
    """
    trace_id: str = Field(..., description="Global Traceability ID")
    
    # 1. Data Payload (Passed to TokenValidator)
    content: Dict[str, Any] = Field(default_factory=dict)
    
    # 2. Semantic Color (Used by CPN Executor for Guard checks)
    topics: List[Topic] = Field(default_factory=list)