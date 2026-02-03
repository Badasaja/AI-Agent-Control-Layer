import sqlite3
import json
from datetime import datetime
from typing import Optional, List
from pydantic import ValidationError
from entity.tokens import Token

class TokenRepository:
    def __init__(self, db_path: str = "tb_cspn.db"):
        self.db_path = db_path
        self._init_schema()

    def _init_schema(self):
        """Token 클래스 필드와 1:1 매핑되는 테이블 생성"""
        ddl = """
        CREATE TABLE IF NOT EXISTS tokens (
            trace_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            history TEXT NOT NULL,      -- List[str] -> JSON Array
            created_at TEXT NOT NULL,   -- datetime -> ISO Format String
            content TEXT NOT NULL,      -- Dict[str, Any] -> JSON Object
            topics TEXT NOT NULL        -- Dict[str, float] -> JSON Object
        );
        -- Lineage 추적 및 그룹핑을 위한 인덱스
        CREATE INDEX IF NOT EXISTS idx_source_id ON tokens(source_id);
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(ddl)

    def save(self, token: 'Token'):
        """Token 객체를 직렬화하여 DB에 저장 (Insert or Update)"""
        query = """
        INSERT OR REPLACE INTO tokens 
        (trace_id, source_id, history, created_at, content, topics)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        # Pydantic v2의 model_dump 모드 활용 가능하나, 명시적 변환이 안전함
        params = (
            token.trace_id,
            token.source_id,
            json.dumps(token.history),
            token.created_at.isoformat(),
            json.dumps(token.content, ensure_ascii=False), # 한글 보존
            json.dumps(token.topics)
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(query, params)
            # conn.commit()은 context manager가 자동 처리하지만 명시 가능

    def load(self, trace_id: str) -> Optional['Token']:
        """DB 레코드를 역직렬화하여 Immutable Token 객체로 복원"""
        query = "SELECT * FROM tokens WHERE trace_id = ?"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row # 컬럼명으로 접근 가능하게 설정
            cursor = conn.execute(query, (trace_id,))
            row = cursor.fetchone()

            if not row:
                return None

            try:
                # DB Row -> Dictionary -> Pydantic Model
                token_data = {
                    "trace_id": row["trace_id"],
                    "source_id": row["source_id"],
                    "history": json.loads(row["history"]),
                    "created_at": datetime.fromisoformat(row["created_at"]),
                    "content": json.loads(row["content"]),
                    "topics": json.loads(row["topics"])
                }
                return Token(**token_data)
                
            except (json.JSONDecodeError, ValidationError) as e:
                print(f"[Error] 토큰 복원 실패 (Corrupted Data): {e}")
                return None

    def get_by_source(self, source_id: str) -> List['Token']:
        """특정 원천 소스에서 파생된 모든 토큰 조회"""
        query = "SELECT trace_id FROM tokens WHERE source_id = ?"
        tokens = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, (source_id,))
            rows = cursor.fetchall()
            for row in rows:
                t = self.load(row[0]) # 재사용성을 위해 load 호출
                if t: tokens.append(t)
        return tokens