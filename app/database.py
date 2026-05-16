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
        await _connection.execute("PRAGMA foreign_keys = ON;")
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
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
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
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
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
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS languages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            level TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            location TEXT DEFAULT '',
            job_type TEXT DEFAULT 'full-time',
            salary TEXT DEFAULT '',
            link TEXT DEFAULT '',
            description TEXT DEFAULT '',
            company_description TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS behavioral_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            selected_option TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS behavioral_profile (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            core_traits TEXT NOT NULL, -- JSON
            operating_styles TEXT NOT NULL, -- JSON
            strategic_insights TEXT NOT NULL, -- JSON
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS job_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            overall_score INTEGER NOT NULL,
            technical_fit INTEGER NOT NULL,
            cultural_fit INTEGER NOT NULL,
            strengths TEXT NOT NULL,
            gaps TEXT NOT NULL,
            red_flags TEXT NOT NULL,
            recommendations TEXT NOT NULL,
            positioning_strategy TEXT NOT NULL,
            analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            UNIQUE(job_id, user_id)
        )
    """)

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS mock_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            interview_type TEXT NOT NULL,
            response_mode TEXT NOT NULL,
            time_per_question INTEGER NOT NULL,
            language TEXT NOT NULL DEFAULT 'en',
            introduction_message TEXT,
            status TEXT NOT NULL DEFAULT 'in_progress',
            questions TEXT NOT NULL,
            inferred_level TEXT NOT NULL DEFAULT 'mid',
            overall_score INTEGER,
            overall_feedback TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        )
    """)
    # Attempt to add the column if the table already exists
    try:
        await conn.execute("ALTER TABLE mock_sessions ADD COLUMN introduction_message TEXT")
    except Exception:
        pass

    await conn.execute("""
        CREATE TABLE IF NOT EXISTS mock_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            question_index INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            question_type TEXT NOT NULL,
            dimension TEXT NOT NULL,
            metric TEXT NOT NULL,
            user_answer TEXT NOT NULL,
            ai_evaluation TEXT NOT NULL,
            score INTEGER NOT NULL DEFAULT 0,
            time_taken INTEGER,
            has_follow_up INTEGER DEFAULT 0,
            follow_up_question TEXT,
            follow_up_answer TEXT,
            follow_up_evaluation TEXT,
            FOREIGN KEY (session_id) REFERENCES mock_sessions(id) ON DELETE CASCADE
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
    await _ensure_columns(conn, "jobs", {
        "job_type": "job_type TEXT DEFAULT 'full-time'",
        "salary": "salary TEXT DEFAULT ''",
        "link": "link TEXT DEFAULT ''",
        "description": "description TEXT DEFAULT ''",
        "company_description": "company_description TEXT DEFAULT ''"
    })


async def _ensure_columns(conn: aiosqlite.Connection, table: str, columns: dict[str, str]):
    async with conn.execute(f"PRAGMA table_info({table})") as cursor:
        rows = await cursor.fetchall()
    existing = {row[1] for row in rows}
    for name, ddl in columns.items():
        if name not in existing:
            await conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
    await conn.commit()