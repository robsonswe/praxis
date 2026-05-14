import pytest
import aiosqlite
import os
from app.database import init_db, get_connection, close_connection

@pytest.fixture
async def test_db(tmp_path):
    # Ensure fresh state for each test
    await close_connection()
    db_file = tmp_path / "test_cascade.db"
    await init_db(db_file)
    conn = await get_connection()
    yield conn
    await close_connection()
    if os.path.exists(db_file):
        os.remove(db_file)

@pytest.mark.asyncio
async def test_user_deletion_cascade(test_db):
    conn = test_db
    
    # 1. Create User
    await conn.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Cascade User", "cascade@test.com"))
    res = await conn.execute("SELECT last_insert_rowid()")
    user_id = (await res.fetchone())[0]
    
    # 2. Create Related Data
    # Job
    await conn.execute("INSERT INTO jobs (user_id, title, company) VALUES (?, ?, ?)", (user_id, "Job 1", "Company 1"))
    res = await conn.execute("SELECT last_insert_rowid()")
    job_id = (await res.fetchone())[0]
    
    # Analysis
    await conn.execute("""
        INSERT INTO job_analysis (job_id, user_id, overall_score, technical_fit, cultural_fit, strengths, gaps, red_flags, recommendations, positioning_strategy)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (job_id, user_id, 80, 80, 80, "[]", "[]", "[]", "[]", "Strategy"))
    
    # Behavioral Response
    await conn.execute("INSERT INTO behavioral_responses (user_id, question_id, selected_option) VALUES (?, ?, ?)", (user_id, 1, "A"))
    
    # AI Settings
    await conn.execute("INSERT INTO ai_settings (user_id, provider, model) VALUES (?, ?, ?)", (user_id, "provider", "model"))
    
    await conn.commit()
    
    # Verify data exists
    async with conn.execute("SELECT COUNT(*) FROM jobs WHERE user_id = ?", (user_id,)) as cursor:
        assert (await cursor.fetchone())[0] == 1
    async with conn.execute("SELECT COUNT(*) FROM job_analysis WHERE user_id = ?", (user_id,)) as cursor:
        assert (await cursor.fetchone())[0] == 1
    async with conn.execute("SELECT COUNT(*) FROM behavioral_responses WHERE user_id = ?", (user_id,)) as cursor:
        assert (await cursor.fetchone())[0] == 1
    async with conn.execute("SELECT COUNT(*) FROM ai_settings WHERE user_id = ?", (user_id,)) as cursor:
        assert (await cursor.fetchone())[0] == 1
        
    # 3. Delete User
    await conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    await conn.commit()
    
    # 4. Verify Cascade
    async with conn.execute("SELECT COUNT(*) FROM jobs WHERE user_id = ?", (user_id,)) as cursor:
        assert (await cursor.fetchone())[0] == 0
    async with conn.execute("SELECT COUNT(*) FROM job_analysis WHERE user_id = ?", (user_id,)) as cursor:
        assert (await cursor.fetchone())[0] == 0
    async with conn.execute("SELECT COUNT(*) FROM behavioral_responses WHERE user_id = ?", (user_id,)) as cursor:
        assert (await cursor.fetchone())[0] == 0
    async with conn.execute("SELECT COUNT(*) FROM ai_settings WHERE user_id = ?", (user_id,)) as cursor:
        assert (await cursor.fetchone())[0] == 0

@pytest.mark.asyncio
async def test_job_deletion_cascade_analysis(test_db):
    conn = test_db
    
    # 1. Setup User and Job
    await conn.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Job User", "job@test.com"))
    res = await conn.execute("SELECT last_insert_rowid()")
    user_id = (await res.fetchone())[0]
    
    await conn.execute("INSERT INTO jobs (user_id, title, company) VALUES (?, ?, ?)", (user_id, "Job to Delete", "Company"))
    res = await conn.execute("SELECT last_insert_rowid()")
    job_id = (await res.fetchone())[0]
    
    # 2. Setup Analysis
    await conn.execute("""
        INSERT INTO job_analysis (job_id, user_id, overall_score, technical_fit, cultural_fit, strengths, gaps, red_flags, recommendations, positioning_strategy)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (job_id, user_id, 90, 90, 90, "[]", "[]", "[]", "[]", "Strategy"))
    await conn.commit()
    
    # 3. Delete Job
    await conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    await conn.commit()
    
    # 4. Verify Analysis is gone
    async with conn.execute("SELECT COUNT(*) FROM job_analysis WHERE job_id = ?", (job_id,)) as cursor:
        assert (await cursor.fetchone())[0] == 0
