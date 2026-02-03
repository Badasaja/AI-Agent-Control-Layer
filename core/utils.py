"""
일반적 유틸리티 함수들을 모아놓은 모듈.
"""
from pathlib import Path
import yaml

def load_cfg(path: str|Path) -> dict:
    with open(path, "r", encoding = "utf-8") as f: return yaml.safe_load(f)

def load_resource_specs(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        # YAML 텍스트를 딕셔너리로 변환
        raw_db = yaml.safe_load(f)
    return raw_db