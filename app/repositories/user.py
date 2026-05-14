from typing import Optional
from app.database import get_connection, close_connection

class UserRepository:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        
    async def initialize(self):
        from app.database import init_db
        if self.db_path != ":memory:":
            from app.database import set_db_path
            set_db_path(self.db_path)
        await init_db()
        
    async def create(self, name: str, email: str) -> dict:
        conn = await get_connection()
        cursor = await conn.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            (name, email)
        )
        await conn.commit()
        return {"id": cursor.lastrowid, "name": name, "email": email}
    
    async def get_by_id(self, user_id: int) -> Optional[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()
    
    async def get_by_name(self, name: str) -> Optional[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM users WHERE name = ?", (name,)) as cursor:
            return await cursor.fetchone()

    async def get_by_email(self, email: str) -> Optional[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute("SELECT * FROM users WHERE email = ?", (email,)) as cursor:
            return await cursor.fetchone()
    
    async def close(self):
        await close_connection()
        
    def set_path(self, path: str):
        from app.database import set_db_path
        set_db_path(path)