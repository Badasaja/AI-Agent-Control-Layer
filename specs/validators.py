from enum import Enum
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, ValidationError
from core import logging_utils

### ============== 커스텀 예외 정의 ============== ###

class SemanticError(Exception):
    """LLM이 개입해 토큰 의미론적 검증 실패 시 발생하는 예외"""
    pass

### ============== 토큰 Validator 정의 ============== ###
## ======== datatype class 정의 ======== ##

# Field Type 내 MixedEnum 방식으로 입력 데이터타입 명세 고정
class FieldType(str, Enum):
    STRING = "string"
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    JSON = "json"

# Field 제약조건 명세
class FieldConstraint(BaseModel):
    type : FieldType
    required : bool = True
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    max_length: Optional[int] = None
    description: Optional[str] = None

# 토큰 스펙 명세
class ResourceSpecModel(BaseModel):
    spec_id: str
    associated_topic: str
    fields: Dict[str, FieldConstraint]

    class Config:
        frozen = True

### ======== validator class 정의 ======== ###

class TokenValidator:
    """
    역할: Token(기차)이 ResourceSpec(철도 규격)을 준수하는지 검사
    - 검증 실패 시 SemanticError raise (즉시 중단)
    - 검증 성공 시 True 반환
    """
    
    def __init__(self, spec_db: Dict[str, dict], logger=None):
        # Logger 이름 고정 (가독성 확보)
        self.logger = logger or logging_utils.get_logger("Validator")
        self.specs: Dict[str, ResourceSpecModel] = {}
        
        for spec_id, raw_data in spec_db.items():
            try:
                self.specs[spec_id] = ResourceSpecModel(**raw_data)
            except ValidationError as e:
                # 초기화 실패는 치명적이므로 Warning 대신 Error 유지하되, 전체 중단 여부는 선택 사항
                self.logger.error(f"[Init] Spec DB 오염됨 ({spec_id}) - {e}")

    def validate(self, token: Dict[str, Any], spec_id: str) -> bool:
        """
        검증 실패 시 raise SemanticError, 성공 시 True 반환
        """
        # 1. 스펙 조회
        spec = self.specs.get(spec_id)
        if not spec:
            msg = f"Unknown Spec ID: {spec_id}"
            self.logger.error(msg)
            raise ValueError(msg)

        self.logger.info(f"토큰 검증 시작 (Spec: {spec_id})")

        # 2. 필드별 순회 검증
        for field_name, rule in spec.fields.items():
            
            # 2-1. 필수 필드 존재 여부
            if field_name not in token:
                if rule.required:
                    self._fail(f"Missing Required Field: '{field_name}'")
                continue # 필수가 아니면 넘어감

            value = token[field_name]

            # 2-2. 타입 검증 & 제약조건 체크
            self._check_constraint(field_name, value, rule)

        return True

    def _check_constraint(self, fname: str, val: Any, rule: FieldConstraint):
        # Type Checking & Constraints
        if rule.type == FieldType.STRING:
            if not isinstance(val, str):
                self._fail(f"'{fname}' must be String (got {type(val).__name__})")
            if rule.max_length and len(val) > rule.max_length:
                self._fail(f"'{fname}' length {len(val)} > {rule.max_length}")

        elif rule.type == FieldType.FLOAT:
            if not isinstance(val, (float, int)):
                self._fail(f"'{fname}' must be Float/Int (got {type(val).__name__})")
            if rule.min_value is not None and val < rule.min_value:
                self._fail(f"'{fname}' value {val} < min {rule.min_value}")
            if rule.max_value is not None and val > rule.max_value:
                self._fail(f"'{fname}' value {val} > max {rule.max_value}")
    
    def _fail(self, message: str):
        """에러 로그 출력 후 예외 발생 (중복 코드 제거용)"""
        self.logger.error(message)
        raise SemanticError(message)