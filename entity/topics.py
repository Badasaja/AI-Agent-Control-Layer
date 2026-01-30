from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

"""
topics.py
목적 : topics 클래스(공통 지식 영역) 정의
"""

# ==========================================
# 1. Enums: TB-CSPN Organizational Structure
# ==========================================

class Topic(BaseModel):
    """
    The semantic coloring of the token.
    """
    id: str
    description: str
    weight: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0.0-1.0)")

