from enum import Enum
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, ValidationError
from core import logging_utils
from datetime import datetime

"""
tokens.py
목적 : 토큰 클래스를 정의함. 
"""
# ==========================================
# 1. Tokens
# ==========================================

class Token(BaseModel):
    """
    Combines Data Payload (for Validator) with Semantic Context
    TokenSpec 준수여부를 확인받는 부분은 content이다. 
    """
    # 0. 내부 Util
    @property
    def first_value(self) -> Any:
        """content의 첫 번째 value 반환 (디버깅용)"""
        if self.content:
            return next(iter(self.content.values()))
        return None

    # 1. 토큰 식별자
    trace_id : str = Field(..., description="고유 토큰 식별자")
    source_id : str = Field(..., description="토큰 출처 식별자")
    history: List[str] = Field(default_factory=list, description="방문한 Task ID 목록")
    created_at: datetime = Field(
        default_factory = datetime.now,
        description="토큰 생성 시점(System TimeStamp)"
    )

    # 2. Data Payload (실질적 점검대상)
    content : Dict[str, Any] = Field(default_factory = dict)

    # 3. Topic attribute
    topics : Dict[str, float] = Field(
        default_factory=dict,
        description = "토큰과 연관된 주제 및 해당 주제의 관련도 점수"
    )

    # 99. 출력 Util
    def __repr__(self):
        """로그 출력 시 가독성을 위한 포맷팅"""
        time_str = self.created_at.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        return (
            f"\n[Token: {self.trace_id}]\n"
            f" ├─ Timestamp: {time_str}\n"
            f" └─ Content  : {self.first_value}...\n"
        )
    class ConfigDict:
        frozen = True