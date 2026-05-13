from typing import Optional
from app.database import get_connection

class AISettingsRepository:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        
    async def initialize(self):
        from app.database import init_db
        if self.db_path != ":memory:":
            from app.database import set_db_path
            set_db_path(self.db_path)
        await init_db()
        
    async def get_by_user(self, user_id: int) -> Optional[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute(
            "SELECT * FROM ai_settings WHERE user_id = ?", (user_id,)
        ) as cursor:
            return await cursor.fetchone()
    
    async def upsert(self, user_id: int, provider: str, model: str,
                     stt_provider: str = "browser", stt_model: str = "Browser Built In", stt_mode: str = "batch",
                     tts_provider: str = "browser", tts_model: str = "Browser Built In") -> dict:
        conn = await get_connection()
        
        existing = await self.get_by_user(user_id)
        
        if existing:
            await conn.execute(
                """UPDATE ai_settings SET provider = ?, model = ?, 
                   stt_provider = ?, stt_model = ?, stt_mode = ?, tts_provider = ?, tts_model = ? 
                   WHERE user_id = ?""",
                (provider, model, stt_provider, stt_model, stt_mode, tts_provider, tts_model, user_id)
            )
        else:
            await conn.execute(
                """INSERT INTO ai_settings (user_id, provider, model, stt_provider, stt_model, stt_mode, tts_provider, tts_model) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, provider, model, stt_provider, stt_model, stt_mode, tts_provider, tts_model)
            )
        await conn.commit()
        
        return {
            "user_id": user_id, 
            "provider": provider, 
            "model": model,
            "stt_provider": stt_provider,
            "stt_model": stt_model,
            "stt_mode": stt_mode,
            "tts_provider": tts_provider,
            "tts_model": tts_model
        }
    
    def set_path(self, path: str):
        from app.database import set_db_path
        set_db_path(path)