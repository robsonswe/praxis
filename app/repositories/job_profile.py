import json
from typing import Optional
from app.database import get_connection
from app.models.job import JobProfile

class JobProfileRepository:
    def _parse_job_profile(self, row: dict) -> JobProfile:
        return JobProfile(
            id=row["id"],
            job_id=row["job_id"],
            user_id=row["user_id"],
            name=row["name"],
            email=row["email"],
            title=row["title"],
            summary=row["summary"],
            location=row["location"],
            years_of_experience=row["years_of_experience"],
            date_of_birth=row["date_of_birth"],
            phone=row["phone"],
            website=row["website"],
            linkedin=row["linkedin"],
            github=row["github"],
            work_experience=json.loads(row["work_experience"]),
            education=json.loads(row["education"]),
            certifications=json.loads(row["certifications"]),
            courses=json.loads(row["courses"]),
            achievements=json.loads(row["achievements"]),
            skills=json.loads(row["skills"]),
            projects=json.loads(row["projects"]),
            languages=json.loads(row["languages"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    async def get_by_job_user(self, job_id: int, user_id: int) -> Optional[JobProfile]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute(
            "SELECT * FROM job_profile WHERE job_id = ? AND user_id = ?",
            (job_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            return self._parse_job_profile(row)

    async def upsert(self, jp: JobProfile) -> JobProfile:
        conn = await get_connection()
        
        await conn.execute(
            """INSERT INTO job_profile (
                job_id, user_id, name, email, title, summary, location, years_of_experience,
                date_of_birth, phone, website, linkedin, github, 
                work_experience, education, certifications, courses, achievements, skills, projects, languages
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id, user_id) DO UPDATE SET
                name = excluded.name,
                email = excluded.email,
                title = excluded.title,
                summary = excluded.summary,
                location = excluded.location,
                years_of_experience = excluded.years_of_experience,
                date_of_birth = excluded.date_of_birth,
                phone = excluded.phone,
                website = excluded.website,
                linkedin = excluded.linkedin,
                github = excluded.github,
                work_experience = excluded.work_experience,
                education = excluded.education,
                certifications = excluded.certifications,
                courses = excluded.courses,
                achievements = excluded.achievements,
                skills = excluded.skills,
                projects = excluded.projects,
                languages = excluded.languages,
                updated_at = CURRENT_TIMESTAMP""",
            (
                jp.job_id, jp.user_id, jp.name, jp.email, jp.title, jp.summary, jp.location, jp.years_of_experience,
                jp.date_of_birth, jp.phone, jp.website, jp.linkedin, jp.github,
                json.dumps(jp.work_experience),
                json.dumps(jp.education),
                json.dumps(jp.certifications),
                json.dumps(jp.courses),
                json.dumps(jp.achievements),
                json.dumps(jp.skills),
                json.dumps(jp.projects),
                json.dumps(jp.languages)
            )
        )
        await conn.commit()
        return await self.get_by_job_user(jp.job_id, jp.user_id)

    async def delete_by_job(self, job_id: int, user_id: int):
        conn = await get_connection()
        await conn.execute("DELETE FROM job_profile WHERE job_id = ? AND user_id = ?", (job_id, user_id))
        await conn.commit()
