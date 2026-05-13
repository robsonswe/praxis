import aiosqlite
from pathlib import Path

_db_path: str | Path = Path(__file__).parent.parent / "data" / "app.db"
_connection: aiosqlite.Connection | None = None

def set_db_path(path: str | Path):
    global _db_path
    _db_path = path

def get_db_path() -> str | Path:
    return _db_path

async def get_connection() -> aiosqlite.Connection:
    global _connection
    if _connection is None:
        _connection = await aiosqlite.connect(get_db_path())
    return _connection

async def close_connection():
    global _connection
    if _connection:
        await _connection.close()
        _connection = None

async def init_db(path: str | Path | None = None):
    global _db_path, _connection
    
    if path:
        set_db_path(path)
    
    db = get_db_path()
    if isinstance(db, Path):
        db.parent.mkdir(parents=True, exist_ok=True)
    
    if _connection is None:
        _connection = await aiosqlite.connect(db)
        await _create_tables(_connection)

async def _create_tables(conn: aiosqlite.Connection):
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
        )
    """)
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            provider TEXT NOT NULL DEFAULT 'openrouter',
            model TEXT NOT NULL DEFAULT 'openai/gpt-4o-mini',
            system_prompt TEXT NOT NULL DEFAULT 'You are a helpful assistant.',
            stt_provider TEXT NOT NULL DEFAULT 'browser',
            stt_model TEXT NOT NULL DEFAULT 'Browser Built In',
            stt_mode TEXT NOT NULL DEFAULT 'batch',
            tts_provider TEXT NOT NULL DEFAULT 'browser',
            tts_model TEXT NOT NULL DEFAULT 'Browser Built In',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    await conn.commit()