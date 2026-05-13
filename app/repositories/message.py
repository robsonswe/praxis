from typing import List
from app.database import get_connection, close_connection

class MessageRepository:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        
    async def initialize(self):
        from app.database import init_db
        if self.db_path != ":memory:":
            from app.database import set_db_path
            set_db_path(self.db_path)
        await init_db()
        
    async def get_by_session(self, session_id: int, limit: int = 100) -> List[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute(
            "SELECT id, session_id, role, content, created_at FROM messages WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
            (session_id, limit)
        ) as cursor:
            return await cursor.fetchall()
    
    async def add(self, session_id: int, role: str, content: str) -> dict:
        conn = await get_connection()
        cursor = await conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )
        await conn.commit()
        return {"id": cursor.lastrowid, "session_id": session_id, "role": role, "content": content}
    
    async def delete_by_session(self, session_id: int):
        conn = await get_connection()
        await conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        await conn.commit()
    
    async def close(self):
        await close_connection()
        
    def set_path(self, path: str):
        from app.database import set_db_path
        set_db_path(path)