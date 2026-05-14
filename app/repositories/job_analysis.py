from typing import Optional
import json
from app.database import get_connection
from app.models.job import JobAnalysis, FitInsight

class JobAnalysisRepository:
    async def get_by_job_user(self, job_id: int, user_id: int) -> Optional[JobAnalysis]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute(
            "SELECT * FROM job_analysis WHERE job_id = ? AND user_id = ?",
            (job_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            
            return JobAnalysis(
                id=row["id"],
                job_id=row["job_id"],
                user_id=row["user_id"],
                overall_score=row["overall_score"],
                technical_fit=row["technical_fit"],
                cultural_fit=row["cultural_fit"],
                strengths=[FitInsight(**s) for s in json.loads(row["strengths"])],
                gaps=[FitInsight(**g) for g in json.loads(row["gaps"])],
                red_flags=[FitInsight(**rf) for rf in json.loads(row["red_flags"])],
                recommendations=json.loads(row["recommendations"]),
                positioning_strategy=row["positioning_strategy"],
                analyzed_at=row["analyzed_at"]
            )

    async def upsert(self, analysis: JobAnalysis) -> JobAnalysis:
        conn = await get_connection()
        
        strengths_json = json.dumps([s.dict() for s in analysis.strengths])
        gaps_json = json.dumps([g.dict() for g in analysis.gaps])
        red_flags_json = json.dumps([rf.dict() for rf in analysis.red_flags])
        recommendations_json = json.dumps(analysis.recommendations)

        await conn.execute(
            """INSERT INTO job_analysis (job_id, user_id, overall_score, technical_fit, cultural_fit, 
                                        strengths, gaps, red_flags, recommendations, positioning_strategy)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(job_id, user_id) DO UPDATE SET
                   overall_score = excluded.overall_score,
                   technical_fit = excluded.technical_fit,
                   cultural_fit = excluded.cultural_fit,
                   strengths = excluded.strengths,
                   gaps = excluded.gaps,
                   red_flags = excluded.red_flags,
                   recommendations = excluded.recommendations,
                   positioning_strategy = excluded.positioning_strategy,
                   analyzed_at = CURRENT_TIMESTAMP""",
            (analysis.job_id, analysis.user_id, analysis.overall_score, analysis.technical_fit, analysis.cultural_fit,
             strengths_json, gaps_json, red_flags_json, recommendations_json, analysis.positioning_strategy)
        )
        await conn.commit()
        return await self.get_by_job_user(analysis.job_id, analysis.user_id)

    async def delete_by_job(self, job_id: int, user_id: int):
        conn = await get_connection()
        await conn.execute("DELETE FROM job_analysis WHERE job_id = ? AND user_id = ?", (job_id, user_id))
        await conn.commit()
