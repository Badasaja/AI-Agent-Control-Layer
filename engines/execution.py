import importlib
import logging
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List
from datetime import datetime
from core import logging_utils
from entity.process import Process

"""
execution.py
목적 : 엔진 클래스(프로세스 Fire 절차) 정의함.
"""

@dataclass
class FiringResult:
    task_id: str
    success: bool
    message: str
    new_token: Optional[Any] = None
    elapsed_ms: float = 0.0
    routes_triggered: int = 0

class ExecEngine:
    """
    핵심 프로세스 실행 엔진
    CSPN의 Transition(Task)을 실행하고, 토큰을 변환/생성하는 역할 수행
    
    내부 절차 : 가드 체크 -> 입력 확인 -> 함수 실행 -> 아웃풋 확인 -> 토큰 갱신 -> 라우팅
    """
    def __init__(self, token_validator):
        self.tv = token_validator
        self.logger = logging_utils.get_logger(f"Engine")

    def run_step(self, process: Process) -> Optional[FiringResult]:
        """
        한 스텝의 태스크를 꺼내 처리함
        """
        # 1. 프로세스 큐에서 Job를 추출
        if not process.token_queue:
            self.logger.warning(f"[RUN] 처리할 토큰이 큐에 없습니다.")
            return None
        
        # 2. 큐에서 토큰과 태스크 아이디 추출
        target_task_id, token = process.token_queue.popleft()
        task = process.tasks[target_task_id]

        start_time = datetime.now()

        # 2. 태스크 실행 전 가드 체크
        if not self._check_guards(task, token):
            return FiringResult(task.task_id, False, message="Guard Condition Failed")
        
        # 3. Input Spec Validation
        try:
            self.tv.validate(token.content, task.input_spec_id)
        except Exception as e:
            # SemanticError, ValueError(Spec 없음) 등 모든 검증 에러 포착   
            self.logger.warning(f"Task {task.task_id} Input Validation Failed: {e}")
            return FiringResult(task.task_id, False, f"Input Spec Fail: {str(e)}")
        
        # 4. 동적 실행
        # task.target은 해당 태스크에 할당된 function 혹은 API 실행을 의미
        try:
            func = self._resolve_function(task.target)
            
            # 실행 : Token Content + task config 주입
            output_content = func(token.content, **task.config)

        except Exception as e:
            self.logger.error(f"Task {task.task_id} Execution Logic Failed: {e}", exc_info=True)
            return FiringResult(task.task_id, False, f"Runtime Execution Error: {str(e)}")

        # 5. [Validator] Output Spec Validation
        try:
            self.tv.validate(output_content, task.output_spec_id)
        except Exception as e:
            self.logger.error(f"Task {task.task_id} Output Validation Failed: {e}", exc_info=True)
            return FiringResult(task.task_id, False, f"Output Spec Fail: {str(e)}")

        # 6. Token Evolution (State Update)
        new_token = self._evolve_token(token, output_content, task)

        # 7. Routing (PetriNet Propagation)
        # Process에게 토큰 도착 알림 (Process 내부 로직으로 병합/대기 수행)
        routes_count = self._propagate_token(process, task, new_token)

        elapsed = (datetime.now()-  start_time).total_seconds() * 1000
        return FiringResult(task.task_id, True, "Success", new_token, elapsed, routes_count)

    ### ===== 내부 로직 ===== ###

    def _check_guards(self, task: Any, token: Any) -> bool:
        """Topic 가중치 기반 실행 조건 평가"""
        if not task.guards:
            return True
        
        token_topics = getattr(token, 'topics', {})
        for guard in task.guards:
            score = token_topics.get(guard.target_topic_id, 0.0)
            if score < guard.min_relevance:
                self.logger.debug(f"Guard Fail: {guard.target_topic_id} ({score} < {guard.min_relevance})")
                return False
        return True

    def _resolve_function(self, target_path: str):
        """'module.path:func_name' 문자열을 실제 함수 객체로 변환"""
        try:
            module_path, func_name = target_path.split(":")
            module = importlib.import_module(module_path)
            return getattr(module, func_name)
        except (ValueError, ImportError, AttributeError) as e:
            raise ImportError(f"Function resolution failed for '{target_path}': {e}")

    def _evolve_token(self, old_token: Any, new_content: Dict, task: Any) -> Any:
        """이전 토큰 승계 및 이력 업데이트"""
        # Token 클래스 정의에 따라 model_copy 또는 생성자 사용
        # 예시: Pydantic model_copy
        new_history = getattr(old_token, 'history', []) + [task.task_id]
        
        return old_token.model_copy(update={
            "content": new_content,
            "history": new_history
        })

    def _propagate_token(self, process: Any, current_task: Any, token: Any) -> int:
        """
        [Routing Logic]
        다음 Task들을 찾아 'Process.arrive_token'을 호출함.
        """
        next_tasks = process.get_next_nodes(current_task.task_id)
        
        if not next_tasks:
            process.completed_tokens.append(token) # End of Chain
            return 0

        triggered = 0
        for next_task in next_tasks:
            # Look-ahead Guard Check: 갈 자격이 있는 경로인가?
            if self._check_guards(next_task, token):
                # [핵심] Process의 Place 로직 호출 (Petri Net 동기화 위임)
                process.arrive_token(
                    from_task_id=current_task.task_id,
                    to_task_id=next_task.task_id,
                    token=token
                )
                triggered += 1
            else:
                self.logger.info(f"Route Ignored: {current_task.task_id} -> {next_task.task_id}")
        
        return triggered
