from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

"""
process.py
목적 : task과 process 클래스(petrinet의 transition에 대응) 정의함.
"""

# ==========================================
# 1. Enums: TB-CSPN Organizational Structure
# ==========================================

class AgentRole(str, Enum):
    """
    TB-CSPN Agent Hierarchy [cite: 54, 301]
    - SUPERVISOR: Strategic oversight, Guard check, Human-in-the-loop
    - CONSULTANT: Semantic processing, Topic extraction (LLM based)
    - WORKER: Operational execution, Deterministic actions
    """
    SUPERVISOR = "SUPERVISOR"
    CONSULTANT = "CONSULTANT"
    WORKER = "WORKER"

class AgentNature(str, Enum):
    """
    Agent Type Definition [cite: 302]
    """
    HUMAN = "HUMAN"
    LLM = "LLM"
    TOOL = "TOOL"  # Refers to 'Automatic' or legacy systems

class Layer(str, Enum):
    """
    Communication Layers 
    - SURFACE: I/O, Interaction entry/exit
    - OBSERVATION: Semantic interpretation, Topic refining
    - COMPUTATION: Core logic execution
    """
    SURFACE = "SURFACE"
    OBSERVATION = "OBSERVATION"
    COMPUTATION = "COMPUTATION"

class TaskType(str, Enum):
    PYTHON_FUNC = "python_func"
    API_CALL = "api_call"
    DOCKER_RUN = "docker_run"


# ==========================================
# 2. Task Specification
# ==========================================

class GuardCondition(BaseModel):
    """
    Petri Net Transition Guard
    Distinct from FieldConstraint
    """
    target_topic_id: str
    min_relevance: float = 0.5
    description: str | None

class TaskSpec(BaseModel):
    """
    Definition of a Transition in TB-CSPN
    실행 계약 명세
    """
    task_id : str = Field(..., description="고유 작업 식별자")
    created_at: datetime = Field(
        default_factory = datetime.now,
        description="태스크 생성 시점(System TimeStamp)"
        )
    description: Optional[str] = None

    # ---- 실행로직 ---- 
    type: TaskType
    target: str # module.path:func or API URL
    config: Dict[str, Any] = Field(default_factory=Dict)

    # ---- TB-CSPN Architecture Constraints ---- 
    layer : Layer
    required_agent_roles : List[AgentRole]
    required_agent_types : List[AgentNature]

    # ---- PetriNet Properties
    # 1. Pre-Condition Check
    guards: List[GuardCondition] = Field(default_factory=list)

    # 2. Data Contract (TokenSpec에서 토큰 명세를 불러오는 규약)
    input_spec_id: str | None
    output_spec_id: str | None

    # 99. 출력 Util
    def __repr__(self):
        """로그 출력 시 가독성을 위한 포맷팅"""
        time_str = self.created_at.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        return (
            f"\n[Token: {self.task_id}]\n"
            f" ├─ Timestamp: {time_str}\n"
            f" └─ Description  : {self.description}...\n"
        )
    class ConfigDict:
        frozen = True

# ==========================================
# 3. Process Specification
# ==========================================

