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
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            title TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            location TEXT DEFAULT '',
            years_of_experience INTEGER DEFAULT 0,
            date_of_birth TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            website TEXT DEFAULT '',
            linkedin TEXT DEFAULT '',
            github TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS work_experience (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            experience_type TEXT DEFAULT 'employment',
            location TEXT DEFAULT '',
            start_date TEXT NOT NULL,
            end_date TEXT,
            current INTEGER DEFAULT 0,
            description TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS education (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            institution TEXT NOT NULL,
            degree TEXT NOT NULL,
            field TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            gpa REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS certifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            issuer TEXT NOT NULL,
            issue_date TEXT NOT NULL,
            expiry_date TEXT,
            credential_id TEXT,
            url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            provider TEXT NOT NULL,
            completion_date TEXT NOT NULL,
            certificate_url TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT DEFAULT '',
            date TEXT NOT NULL,
            organization TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            proficiency INTEGER DEFAULT 3,
            years_of_experience INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            role TEXT DEFAULT '',
            technologies TEXT DEFAULT '',
            outcomes TEXT DEFAULT '',
            start_date TEXT NOT NULL,
            end_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    await conn.commit()

    await _ensure_columns(conn, "users", {
        "phone": "phone TEXT DEFAULT ''",
        "website": "website TEXT DEFAULT ''",
        "linkedin": "linkedin TEXT DEFAULT ''",
        "github": "github TEXT DEFAULT ''"
    })
    await _ensure_columns(conn, "work_experience", {
        "experience_type": "experience_type TEXT DEFAULT 'employment'"
    })


async def _ensure_columns(conn: aiosqlite.Connection, table: str, columns: dict[str, str]):
    async with conn.execute(f"PRAGMA table_info({table})") as cursor:
        rows = await cursor.fetchall()
    existing = {row[1] for row in rows}
    for name, ddl in columns.items():
        if name not in existing:
            await conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
    await conn.commit()