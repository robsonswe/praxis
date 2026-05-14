from typing import Optional
from app.database import get_connection


class JobRepository:
    async def create(self, user_id: int, title: str, company: str, location: str, job_type: str,
                     salary: str, link: str, description: str, company_description: str) -> dict:
        conn = await get_connection()
        cursor = await conn.execute(
            """INSERT INTO jobs (user_id, title, company, location, job_type, salary, link, description, company_description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, title, company, location, job_type, salary, link, description, company_description)
        )
        await conn.commit()
        return {
            "id": cursor.lastrowid,
            "user_id": user_id,
            "title": title,
            "company": company,
            "location": location,
            "job_type": job_type,
            "salary": salary,
            "link": link,
            "description": description,
            "company_description": company_description
        }

    async def list_by_user(self, user_id: int) -> list[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute(
            "SELECT * FROM jobs WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        ) as cursor:
            return await cursor.fetchall()

    async def get_by_id(self, job_id: int, user_id: int) -> Optional[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute(
            "SELECT * FROM jobs WHERE id = ? AND user_id = ?",
            (job_id, user_id)
        ) as cursor:
            return await cursor.fetchone()

    async def delete(self, job_id: int, user_id: int) -> bool:
        conn = await get_connection()
        cursor = await conn.execute(
            "DELETE FROM jobs WHERE id = ? AND user_id = ?",
            (job_id, user_id)
        )
        await conn.commit()
        return cursor.rowcount > 0
