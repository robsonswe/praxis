import json
from typing import Optional
from app.database import get_connection


class MockInterviewRepository:

    async def create_session(self, user_id: int, job_id: int, interview_type: str,
                             response_mode: str, time_per_question: int, language: str,
                             introduction_message: str, questions: list[dict], inferred_level: str) -> dict:
        conn = await get_connection()
        cursor = await conn.execute(
            """INSERT INTO mock_sessions
               (user_id, job_id, interview_type, response_mode, time_per_question, language, introduction_message, questions, inferred_level, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'in_progress')""",
            (user_id, job_id, interview_type, response_mode, time_per_question,
             language, introduction_message, json.dumps(questions), inferred_level)
        )
        await conn.commit()
        return {
            "id": cursor.lastrowid,
            "user_id": user_id,
            "job_id": job_id,
            "interview_type": interview_type,
            "response_mode": response_mode,
            "time_per_question": time_per_question,
            "language": language,
            "introduction_message": introduction_message,
            "questions": questions,
            "inferred_level": inferred_level,
            "status": "in_progress"
        }

    async def get_session(self, session_id: int, user_id: int) -> Optional[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute(
            "SELECT * FROM mock_sessions WHERE id = ? AND user_id = ?",
            (session_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                row["questions"] = json.loads(row["questions"])
                if row["overall_feedback"]:
                    row["overall_feedback"] = json.loads(row["overall_feedback"])
            return row

    async def list_sessions(self, user_id: int, job_id: int = None) -> list[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        if job_id:
            query = "SELECT * FROM mock_sessions WHERE user_id = ? AND job_id = ? ORDER BY started_at DESC"
            params = (user_id, job_id)
        else:
            query = "SELECT * FROM mock_sessions WHERE user_id = ? ORDER BY started_at DESC"
            params = (user_id,)
        async with conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                row["questions"] = json.loads(row["questions"])
                if row.get("overall_feedback"):
                    row["overall_feedback"] = json.loads(row["overall_feedback"])
            return rows

    async def complete_session(self, session_id: int, overall_score: int,
                               overall_feedback: dict) -> bool:
        conn = await get_connection()
        cursor = await conn.execute(
            """UPDATE mock_sessions
               SET status = 'completed', overall_score = ?, overall_feedback = ?,
                   completed_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (overall_score, json.dumps(overall_feedback), session_id)
        )
        await conn.commit()
        return cursor.rowcount > 0

    async def save_answer(self, session_id: int, question_index: int, question_text: str,
                          question_type: str, dimension: str, metric: str,
                          user_answer: str, ai_evaluation: dict, score: int,
                          time_taken: int = None, has_follow_up: bool = False,
                          follow_up_question: str = None) -> dict:
        conn = await get_connection()
        cursor = await conn.execute(
            """INSERT INTO mock_answers
               (session_id, question_index, question_text, question_type, dimension, metric,
                user_answer, ai_evaluation, score, time_taken, has_follow_up, follow_up_question)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, question_index, question_text, question_type, dimension, metric,
             user_answer, json.dumps(ai_evaluation), score, time_taken,
             1 if has_follow_up else 0, follow_up_question)
        )
        await conn.commit()
        return {"id": cursor.lastrowid, "session_id": session_id, "question_index": question_index}

    async def save_follow_up(self, session_id: int, question_index: int,
                             follow_up_answer: str, follow_up_evaluation: dict) -> bool:
        new_score = follow_up_evaluation.get("score")
        conn = await get_connection()
        cursor = await conn.execute(
            """UPDATE mock_answers
               SET follow_up_answer = ?, follow_up_evaluation = ?, score = ?
               WHERE session_id = ? AND question_index = ?""",
            (follow_up_answer, json.dumps(follow_up_evaluation), new_score, session_id, question_index)
        )
        await conn.commit()
        return cursor.rowcount > 0

    async def get_answers(self, session_id: int) -> list[dict]:
        conn = await get_connection()
        conn.row_factory = lambda c, r: dict(zip([d[0] for d in c.description], r))
        async with conn.execute(
            "SELECT * FROM mock_answers WHERE session_id = ? ORDER BY question_index",
            (session_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                row["ai_evaluation"] = json.loads(row["ai_evaluation"]) if row.get("ai_evaluation") else None
                row["follow_up_evaluation"] = json.loads(row["follow_up_evaluation"]) if row.get("follow_up_evaluation") else None
                row["has_follow_up"] = bool(row.get("has_follow_up"))
            return rows
