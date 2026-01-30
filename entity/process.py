from enum import Enum
from pydantic import BaseModel, Field, ValidationError
from datetime import datetime
from typing import Dict, List, Deque, Any, Optional
from collections import deque, defaultdict
import logging
from core import logging_utils
from dataclasses import dataclass


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
    PYTHON_FUNC = "python_func" # LLM Invoke도 Python Func의 일종이다
    API_CALL = "api_call"
    DOCKER_RUN = "docker_run" # 기타등등. 

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

class MergeStrategy(str, Enum):
    UNION = "union" # 단순 병합
    STRICT = "strict" # spec 통과를 위한 엄격한 병합
    CUSTOM = "custom_logic" # 의미론적 병합이 필요한 경우 

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
    config: Dict[str, Any] = Field(default_factory=Dict) # target func에게 전달됨

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

    # 3. Task 병합 전략 (기본 : STRICT)
    merge_strategy : MergeStrategy = MergeStrategy.STRICT

    class ConfigDict:
        frozen = True

# ==========================================
# 3. Process Specification
# ==========================================

class Process:
    """
    Graph Topology & Token State Container
    책임 : Task 간 연결 관리 및 현재 토큰 위치 추적
    PetriNet의 철학을 따름.
    """

    def __init__(self, process_id : str):
        # Registry & Graph
        self.process_id = process_id
        self.tasks : Dict[str, TaskSpec] = {} # {task_id : TaskSpec 객체}
        self.graph : Dict[str, List[str]] = defaultdict(list) # {source_id: [target_id_1, target_id_2]}. 신규생성 key는 무조건 list를 지님

        # Runtime State
        self.token_queue : Deque[tuple[str, Any]] = deque() # [(target_task_id, token_obj)]
        self.completed_tokens: List[Any] = [] # 처리 완료 토큰 보관소

        self.logger = logging_utils.get_logger(f"Proc_{process_id}")
        self.is_compiled = False # 컴파일 완료 여부 플래그
        self.error_count = 0

        # Buffer State
        self.pending_buffers : Dict[str, Dict[str, Any]] = defaultdict(dict)
        # 각 Task 실행을 위한 선행 Task의 목록
        self.predecessors: Dict[str, set] = defaultdict(set)

    def add_task(self, task : TaskSpec):
        # 프로세스 정의는 add_task와 add_link로 이행하는 것을 권고
        if task.task_id in self.tasks:
            self.logger.warning(f"Task ID {task.task_id} already exists. Overwriting")
        self.tasks[task.task_id] = task

    def add_link(self, source : str | TaskSpec, target : str | TaskSpec):
        """
        Task 연결
        """
        # 1. 입력이 객체면 ID 추출, 문자열이면 그대로 사용
        src_id = source.task_id if hasattr(source, "task_id") else source
        tgt_id = target.task_id if hasattr(target, "task_id") else target

        # 2. 등록 여부 확인
        if src_id not in self.tasks:
            raise ValueError(f"Source task '{src_id}' not registered")
        if tgt_id not in self.tasks:
            raise ValueError(f"Target task '{tgt_id}' not registered")
        
        # 3. 그래프 연결 (String Key 사용 보장)
        self.graph[src_id].append(tgt_id) 
        self.is_compiled = False

        # 4. 선행 Task 정보 갱신
        self.predecessors[tgt_id].add(src_id)
    
    def compile(self, chain_validator) -> bool:
        """
        Static Engine Phase
        엔진 가동 전 정의된 그래프의 무결성 검증. 

        검증항목
        1. Token Spec 호환성
        2. 구조적 데드락 검증 - Directed Acyclity 강제

        검증 모두 통과시 is_compiled=TRUE
        """
        # 1. Spec Compatibility 검증
        for source_id, target_ids in self.graph.items():
            source_task = self.tasks[source_id]
            for target_id in target_ids:
                target_task = self.tasks[target_id]
                if not chain_validator.validate_link(source_task, target_task):
                    self.logger.error(f"[SPEC CHAIN ERROR] {source_id} -> {target_id} mismatch")
                    self.error_count += 1
                
        # 2. 데드락 검증
        if self._detect_cycle():
            self.logger.error("[TOPOLOGY ERROR] 데드락 발생! ")
            self.error_count += 1

        if self.error_count > 0:
            self.logger.critical(f"[COMPILE FAILURE] : {self.error_count} errors.")
            return False
        
        # 검증 전부 통과시 True Return
        self.is_compiled = True
        self.logger.info(f"[COMPILE SUCCESS] Spec 일치 & Process Topology 정상.")
        return True
    
    def inject_token(self, start_task_id : str, token: Any):
        """
        [RUNTIME ENTRY POINT]
        초기 토큰을 특정 시작 task에 주입
        """
        if not self.is_compiled:
            self.logger.warning("[WARNING]: Process가 컴파일되지 않고 실행중입니다.")

        if start_task_id not in self.tasks:
            raise ValueError(f"Entry task {start_task_id}가 task registry에서 확인되지 않습니다. add_task를 해주세요")
        
        # 시작 TASK의 Input Spec과 토큰이 맞는지 체크는 Engine레벨에서 수행
        self.token_queue.append((start_task_id, token))
        self.logger.info(f"토큰 주입 = {start_task_id}")

    def arrive_token(self, from_task_id : str, to_task_id : str, token : Any):
        """
        토큰이 특정 Task의 입력 플레이스에 도착했을 때의 처리 로직
        """
        # 1. 대기실(Buffer State에 토큰 저장)
        self.pending_buffers[to_task_id][from_task_id] = token

        # 2. 조건 검사 : Predecessors가 전부 모였는지 여부
        required_sources = self.predecessors[to_task_id]
        arrived_sources = set(self.pending_buffers[to_task_id].keys())

        missing = required_sources - arrived_sources

        if not missing: 
            # 모든 재료 도착 시 실행
            target_task_spec = self.tasks[to_task_id]
            
            # [핵심] Task의 전략에 따라 토큰 병합 방식 결정
            merged_token = self._apply_merge_strategy(
                target_task_spec.merge_strategy, 
                list(self.pending_buffers[to_task_id].values())
            )
            
            self.token_queue.append((to_task_id, merged_token))
            self.pending_buffers[to_task_id].clear()

        else:
            self.logger(f"[INFO] 대기중 - {to_task_id}가 {missing} 태스크 완료를 대기중")

    def get_next_nodes(self, current_task_id: str) -> List[TaskSpec]:
        """
        현재 Task 완료 후 이동 가능한 후보 Task 리스트 반환
        실행 엔진의 Rounting 단계에서 호출될 메서드
        """
        # graph 내에서 현재 노드의 다음 가능한 노드 리스트를 리턴
        next_ids = self.graph.get(current_task_id, [])
        
        # 실제 TaskSpec 객체 리스트 반환
        return [self.tasks[nid] for nid in next_ids]
    
    def get_task(self, task_id : str) -> Optional[TaskSpec]:
        " task id로 TaskSpec를 조회하는 메서드"
        return self.tasks.get(task_id)

    # (2. 데드락 검증)을 위한 검증 함수
    def _detect_cycle(self) -> bool:
        """
        DFS를 이용한 순환 참조(Cycle) 탐지
        순환 참조 존재시 True 리턴
        이외에 False 리턴
        """
        visited = set()
        recursion_stack = set()

        def dfs(node_id):   
            visited.add(node_id)
            recursion_stack.add(node_id)

            for neighbor_id in self.graph.get(node_id, []):
                if neighbor_id not in visited:
                    if dfs(neighbor_id):
                        return True
                elif neighbor_id in recursion_stack:
                    # 방문 중인 경로에 다시 도달 -> Cycle 발생
                    self.logger.error(f"Cycle detected at node: {neighbor_id}")
                    return True
            
            recursion_stack.remove(node_id)
            return False

        # 모든 노드에 대해 DFS 수행 (단절된 그래프 고려)
        for node_id in self.tasks:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        return False
    
    # (명시된 토큰 병합 로직에 따른 케이스 구분)
    def _apply_merge_strategy(self, strategy: MergeStrategy, tokens: List[Any]) -> Any:
        base = tokens[0]
        
        if strategy == MergeStrategy.CUSTOM:
            # [Semantic Merge] 합치지 않음! 
            # 데이터를 리스트로 묶어서 포장함 -> {"__inputs__": [content_A, content_B]}
            # 이렇게 하면 Task C의 함수가 이걸 받아서 알아서 판단함.
            combined_content = {
                "__inputs__": [t.content for t in tokens],
                "__meta__": "bundled"
            }
            return base.__class__(trace_id=base.trace_id, content=combined_content)

        elif strategy == MergeStrategy.STRICT:
            # [System Merge] 엔진이 대신 합쳐줌 (기존 로직 + 충돌 체크)
            new_content = {}
            for t in tokens:
                for k, v in t.content.items():
                    if k in new_content and new_content[k] != v:
                        raise ValueError(f"Merge Conflict: {k}")
                    new_content[k] = v
            return base.__class__(trace_id=base.trace_id, content=new_content)
            
        else: # UNION
            # [Lazy Merge] 덮어쓰기 허용
            new_content = {}
            for t in tokens:
                new_content.update(t.content)
            return base.__class__(trace_id=base.trace_id, content=new_content)