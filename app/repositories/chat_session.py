from typing import Optional, List
from app.database import get_connection

class ChatSessionRepository:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        
    async def initialize(self):
        from app.database import init_db
        if self.db_path != ":memory:":
            from app.database import set_db_path
            set_db_path(self.db_path)
        await init_db()
        
    async def create(self, user_id: int, title: str) -> dict:
        conn = await get_connection()
        cursor = await conn.execute(
            "INSERT INTO chat_sessions (user_id, title) VALUES (?, ?)",
            (user_id, title)
        )
        await conn.commit()
        return {"id": cursor.lastrowid, "user_id": user_id, "title": title}
    
    async def get_by_user(self, user_id: int) -> List[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute(
            "SELECT * FROM chat_sessions WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ) as cursor:
            return await cursor.fetchall()
    
    async def get_by_id(self, session_id: int) -> Optional[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,)) as cursor:
            return await cursor.fetchone()
    
    async def delete(self, session_id: int):
        conn = await get_connection()
        await conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
        await conn.commit()

    async def update_title(self, session_id: int, title: str):
        conn = await get_connection()
        await conn.execute("UPDATE chat_sessions SET title = ? WHERE id = ?", (title, session_id))
        await conn.commit()
        
    def set_path(self, path: str):
        from app.database import set_db_path
        set_db_path(path)