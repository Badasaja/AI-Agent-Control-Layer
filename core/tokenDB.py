import sqlite3
import json, os, re
from datetime import datetime
from typing import Optional, List
from pydantic import ValidationError
from entity.tokens import Token

class TokenRepository:
    def __init__(self, db_path: str = "./data/tb_cspn.db", table_name: str = "tokens"):
        self.db_path = db_path
        self.table_name = self._validate_table_name(table_name) # SQL Injection 방지
        self._ensure_directory()
        self._init_schema()

    def _ensure_directory(self):
        """DB 파일 경로의 디렉토리가 없으면 생성"""
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def _validate_table_name(self, name: str) -> str:
        """테이블명 유효성 검사 (알파벳, 숫자, 언더스코어만 허용)"""
        if not re.match(r"^[a-zA-Z0-9_]+$", name):
            raise ValueError(f"Invalid table name: {name}")
        return name

    def _init_schema(self):
        """동적 테이블명을 사용하여 스키마 초기화"""
        # f-string을 사용하여 테이블명 주입
        ddl = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            trace_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            history TEXT NOT NULL,      -- JSON Array
            created_at TEXT NOT NULL,   -- ISO Format
            content TEXT NOT NULL,      -- JSON Object
            topics TEXT NOT NULL        -- JSON Object
        );
        CREATE INDEX IF NOT EXISTS idx_{self.table_name}_source ON {self.table_name}(source_id);
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(ddl)

    def save(self, token: 'Token'):
        """지정된 테이블에 토큰 저장"""
        query = f"""
        INSERT OR REPLACE INTO {self.table_name} 
        (trace_id, source_id, history, created_at, content, topics)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        params = (
            token.trace_id,
            token.source_id,
            json.dumps(token.history),
            token.created_at.isoformat(),
            json.dumps(token.content, ensure_ascii=False),
            json.dumps(token.topics)
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(query, params)

    def load(self, trace_id: str) -> Optional['Token']:
        """지정된 테이블에서 토큰 조회"""
        query = f"SELECT * FROM {self.table_name} WHERE trace_id = ?"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, (trace_id,))
            row = cursor.fetchone()

            if not row: return None

            try:
                token_data = {
                    "trace_id": row["trace_id"],
                    "source_id": row["source_id"],
                    "history": json.loads(row["history"]),
                    "created_at": datetime.fromisoformat(row["created_at"]),
                    "content": json.loads(row["content"]),
                    "topics": json.loads(row["topics"])
                }
                return Token(**token_data) # Token 클래스는 외부에서 import 가정
                
            except (json.JSONDecodeError, ValidationError) as e:
                print(f"[Error] Data Corruption in {self.table_name}: {e}")
                return None

    def get_by_source(self, source_id: str) -> List['Token']:
        """특정 소스의 토큰 일괄 조회"""
        query = f"SELECT trace_id FROM {self.table_name} WHERE source_id = ?"
        tokens = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, (source_id,))
            rows = cursor.fetchall()
            for row in rows:
                t = self.load(row[0])
                if t: tokens.append(t)
        return tokens