import json
from pathlib import Path
from typing import Optional
from app.repositories.mock_interview import MockInterviewRepository
from app.repositories.job import JobRepository
from app.services.ai_service import AIService

MATRIX_PATH = Path(__file__).parent.parent / "resources" / "interview_matrix.json"

# The 25 behavioral metrics organized by dimension
BEHAVIORAL_DIMENSIONS = {
    "Execução e Autonomia": [
        "Curva de Aprendizado e Resourcefulness",
        "Organização e Quebra de Escopo",
        "Limite de Autonomia",
        "Disciplina Operacional"
    ],
    "Decisão, Pressão e Ambiguidade": [
        "Priorização sob Pressão",
        "Gestão de Ambiguidade",
        "Negociação e Limites",
        "Adaptação a Mudanças"
    ],
    "Inteligência Interpessoal e Colaboração": [
        "Conflito Técnico e Discordância",
        "Desafiar com Respeito",
        "Lidar com Erros de Terceiros",
        "Liderança Indireta",
        "Inclusão e Diversidade de Pensamento"
    ],
    "Comunicação e Alinhamento": [
        "Prevenção de Retrabalho",
        "Comunicação Não-Técnica",
        "Transparência e Visibilidade Ativa"
    ],
    "Resiliência, Erro e Autoavaliação": [
        "Receptividade a Feedback Corretivo",
        "Gestão do Próprio Erro",
        "Autoavaliação",
        "Reação ao Fracasso"
    ],
    "Propósito, Ética e Valores": [
        "Motivação Sustentável",
        "Valores Inegociáveis",
        "Dilemas Éticos e Accountability",
        "Inovação vs. Estabilidade",
        "Visão de Evolução"
    ]
}


from app.services.profile import ProfileService

class MockInterviewService:
    def __init__(self, repository: MockInterviewRepository,
                 job_repository: JobRepository,
                 profile_service: ProfileService,
                 ai_service: AIService):
        self.repository = repository
        self.job_repository = job_repository
        self.profile_service = profile_service
        self.ai_service = ai_service

    async def generate_questions(self, user_id: int, job_id: int,
                                 interview_type: str, language: str = "en") -> dict:
        """Generate interview questions using AI based on job context and interview type."""
        job = await self.job_repository.get_by_id(job_id, user_id)
        if not job:
            raise Exception("Job not found")

        profile = await self.profile_service.get_profile(user_id)
        profile_text = "No profile provided."
        if profile:
            from datetime import datetime
            age_text = ""
            if profile.date_of_birth:
                try:
                    dob = datetime.strptime(profile.date_of_birth, "%Y-%m-%d")
                    age = (datetime.now() - dob).days // 365
                    age_text = f"Age: {age}\n"
                except:
                    pass
            profile_text = f"Name: {profile.name}\n{age_text}Title: {profile.title}\nSummary: {profile.summary}\nYears of Experience: {profile.years_of_experience}\n"
            if profile.work_experience:
                profile_text += "Experience:\n" + "\n".join([f"- {w.title} at {w.company}, {w.start_date} to {w.end_date or 'Present'}): {w.description}" for w in profile.work_experience])
            if profile.education:
                profile_text += "\nEducation:\n" + "\n".join([f"- {e.degree} in {e.field} from {e.institution} ({e.start_date} to {e.end_date})" for e in profile.education])
            if profile.certifications:
                profile_text += "\nCertifications:\n" + "\n".join([f"- {c.name} by {c.issuer} (Issued: {c.issue_date})" for c in profile.certifications])
            if profile.courses:
                profile_text += "\nCourses:\n" + "\n".join([f"- {c.name} at {c.provider} ({c.completion_date}): {c.description or ''}" for c in profile.courses])
            if profile.achievements:
                profile_text += "\nAchievements:\n" + "\n".join([f"- {a.title} ({a.category}, {a.date}): {a.description}" for a in profile.achievements])
            if profile.projects:
                profile_text += "\nProjects:\n" + "\n".join([f"- {p.name} ({p.start_date} to {p.end_date or 'Present'}): Role: {p.role}. Desc: {p.description}. Tech: {', '.join(p.technologies)}. Outcomes: {', '.join(p.outcomes)}." for p in profile.projects])
            if profile.skills:
                profile_text += "\nSkills: " + ", ".join([f"{s.name} ({s.proficiency}/5)" for s in profile.skills])

        matrix_text = ""
        matrix_data = None
        if MATRIX_PATH.exists():
            with open(MATRIX_PATH, "r", encoding="utf-8") as f:
                matrix_data = json.load(f)
                matrix_text = json.dumps(matrix_data, indent=2, ensure_ascii=False)

        behavioral_block = ""
        if interview_type in ("behavioral", "mixed"):
            behavioral_block = f"""
BEHAVIORAL QUESTION GUIDELINES:
You have access to the following competency matrix with 25 behavioral metrics across 6 dimensions.
Select the most relevant metrics for this specific role and level.
The matrix is provided as a reference. Craft original questions inspired by these metrics.

COMPETENCY MATRIX:
{matrix_text}

DIMENSION PRIORITY BY LEVEL:
- Intern/Junior: Focus on Dimensions 1 (Execution & Autonomy), 5 (Resilience & Self-Awareness), 3 (Collaboration)
- Mid-level: Balanced across all dimensions
- Senior/Lead: Focus on Dimensions 2 (Crisis Management), 4 (Communication), 6 (Ethics & Values)
- Director/Executive: Heavy focus on Dimensions 6 (Ethics & Values), 2 (Crisis Management), 4 (Communication)
"""

        technical_block = ""
        if interview_type in ("technical", "mixed"):
            technical_block = """
TECHNICAL QUESTION GUIDELINES:
Generate questions that test the HARD SKILLS required by this job description.
These are NOT limited to software engineering. The job could be in any field.
Focus on:
- Domain-specific knowledge and practical problem-solving
- Analytical and critical thinking within the field
- Process methodology and best practices relevant to the role
- Tool and technology proficiency mentioned in the description
- System design or strategic thinking appropriate to the level

IMPORTANT: Adjust complexity to the inferred level. An intern gets fundamentals; a director gets strategic architecture.
"""

        if interview_type == "behavioral":
            question_count = "EXACTLY 12 core questions (You MUST generate exactly 2 questions for EACH of the 6 dimensions in the matrix. For each dimension, choose 2 DISTINCT metrics/numbered items from the matrix to base your questions on. Do not repeat metrics.)\nMake sure to output the correct 'dimension_id' and 'metric_id' integers for each core question."
        elif interview_type == "technical":
            question_count = "EXACTLY 8 core questions"
        else:
            question_count = "EXACTLY 10 core questions (6 behavioral - one for each dimension - and 4 technical)"

        prompt = f"""You are a professional interviewer. Generate interview questions for the following role.

JOB CONTEXT:
- Title: {job['title']}
- Company: {job['company']}
- Description: {job['description']}
- Company Context: {job.get('company_description', 'Not provided')}

CANDIDATE PROFILE:
{profile_text}

INTERVIEW TYPE: {interview_type}
TARGET QUESTION COUNT: {question_count}
LANGUAGE: All questions and evaluation_criteria MUST be written in the language with code "{language}".

INSTRUCTIONS:
1. Infer the seniority level from the job title and description.
2. Generate exactly TARGET QUESTION COUNT questions appropriate for that level, focusing ONLY on the core competencies based on the matrix/technical guidelines.
3. IN ADDITION to those core questions, generate a specific warm-up question, a background question based on the user's profile, and a closing question.
4. Each question must feel natural and conversational.

{behavioral_block}
{technical_block}

OUTPUT FORMAT:
You MUST return ONLY a valid JSON object with this exact structure:
{{
    "inferred_level": "intern|junior|mid|senior|lead|director",
    "introduction_message": "A welcoming introductory message as the interviewer. Mention the candidate's name. Do NOT summarize or mention their profile, age, summary, or years of experience.",
    "warm_up_question": {{
        "type": "behavioral",
        "dimension": "Introduction",
        "metric": "Warm-up",
        "text": "Ask the candidate to introduce themselves briefly.",
        "evaluation_criteria": "What a strong answer looks like"
    }},
    "background_question": {{
        "type": "behavioral",
        "dimension": "Background",
        "metric": "Experience",
        "text": "The actual interview question, tailored to their specific background",
        "evaluation_criteria": "What a strong answer looks like"
    }},
    "core_questions": [
        {{
            "type": "behavioral",
            "dimension_id": 1,
            "metric_id": 4,
            "dimension": "Dimension name from the matrix",
            "metric": "Specific metric name",
            "text": "The actual interview question",
            "evaluation_criteria": "What a strong answer looks like at this level"
        }}
    ],
    "closing_question": {{
        "type": "behavioral",
        "dimension": "Closing",
        "metric": "Closing",
        "text": "A final question for the candidate to pitch themselves (e.g., 'Why should we hire you?'). Do NOT ask if they have questions for you.",
        "evaluation_criteria": "What a strong answer looks like"
    }}
}}

For technical questions, use descriptive dimension and metric names relevant to the job field.
Return ONLY the JSON. No markdown, no explanations."""

        max_retries = 3
        last_error = ""

        for attempt in range(max_retries):
            try:
                await self.ai_service.initialize()
                response = await self.ai_service.send_message(
                    user_id, "Interviewer", 0,
                    [{"role": "user", "content": prompt}]
                )

                if "error" in response:
                    raise Exception(f"AI Provider Error: {response['error']}")

                content = response["content"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                data = json.loads(content)

                # Validate structure
                if "core_questions" not in data or not isinstance(data["core_questions"], list):
                    raise ValueError("Missing or invalid 'core_questions' array")
                
                # Enforce counts
                if interview_type == "behavioral" and len(data["core_questions"]) != 12:
                    raise ValueError(f"Expected exactly 12 core questions for behavioral, got {len(data['core_questions'])}")
                elif interview_type == "technical" and len(data["core_questions"]) != 8:
                    raise ValueError(f"Expected exactly 8 core questions for technical, got {len(data['core_questions'])}")
                elif interview_type == "mixed" and len(data["core_questions"]) != 10:
                    raise ValueError(f"Expected exactly 10 core questions for mixed, got {len(data['core_questions'])}")
                    
                # Strict Matrix Validation
                if interview_type == "behavioral" and matrix_data:
                    dim_counts = {}
                    for q in data["core_questions"]:
                        d_id = q.get("dimension_id")
                        m_id = q.get("metric_id")
                        if not isinstance(d_id, int) or not isinstance(m_id, int):
                            raise ValueError("Behavioral questions MUST include integer 'dimension_id' and 'metric_id'.")
                        
                        if d_id not in dim_counts:
                            dim_counts[d_id] = set()
                        dim_counts[d_id].add(m_id)
                    
                    if len(dim_counts) != 6:
                        raise ValueError(f"Expected exactly 6 unique dimensions, got {len(dim_counts)}")
                        
                    for d_id, metrics in dim_counts.items():
                        if len(metrics) != 2:
                            raise ValueError(f"Expected exactly 2 distinct metrics for dimension {d_id}, got {len(metrics)}")

                for required in ["warm_up_question", "background_question", "closing_question"]:
                    if required not in data:
                        raise ValueError(f"Missing '{required}' in AI response")

                # Programmatically assemble the questions in order
                questions = [
                    data["warm_up_question"],
                    data["background_question"]
                ] + data["core_questions"] + [
                    data["closing_question"]
                ]

                # Normalize indices
                for i, q in enumerate(questions):
                    q["index"] = i

                data["questions"] = questions
                return data

            except json.JSONDecodeError:
                last_error = "AI returned invalid JSON"
                continue
            except Exception as e:
                if "AI Provider Error" in str(e):
                    raise
                last_error = str(e)
                continue

        raise Exception(f"Failed to generate questions after {max_retries} attempts: {last_error}")

    async def start_session(self, user_id: int, config: dict) -> dict:
        """Generate questions and create a new interview session."""
        result = await self.generate_questions(
            user_id, config["job_id"], config["interview_type"], config.get("language", "en")
        )

        session = await self.repository.create_session(
            user_id=user_id,
            job_id=config["job_id"],
            interview_type=config["interview_type"],
            response_mode=config["response_mode"],
            time_per_question=config["time_per_question"],
            language=config.get("language", "en"),
            introduction_message=result.get("introduction_message", "Hello! Let's begin the interview."),
            questions=result["questions"],
            inferred_level=result.get("inferred_level", "mid")
        )

        return session

    async def evaluate_answer(self, user_id: int, session_id: int,
                              question_index: int, user_answer: str,
                              time_taken: int = None) -> dict:
        """Evaluate a user's answer and decide if a follow-up is needed."""
        session = await self.repository.get_session(session_id, user_id)
        if not session:
            raise Exception("Session not found")

        questions = session["questions"]
        if question_index >= len(questions):
            raise Exception("Invalid question index")

        question = questions[question_index]
        job = await self.job_repository.get_by_id(session["job_id"], user_id)
        language = session.get("language", "en")

        closing_instruction = ""
        if question.get("dimension") == "Closing" or question_index == len(questions) - 1:
            closing_instruction = "\n7. CRITICAL: This is the final Closing question. DO NOT ask a follow-up. Set 'needs_follow_up' to false."

        prompt = f"""You are evaluating a candidate's answer in a mock interview.

CONTEXT:
- Role: {job['title']} at {job['company']}
- Candidate Level: {session['inferred_level']}
- Question Type: {question['type']}
- Dimension: {question['dimension']}
- Metric: {question['metric']}
- Language: Respond in the language with code "{language}"

QUESTION ASKED:
{question['text']}

EVALUATION CRITERIA:
{question['evaluation_criteria']}

CANDIDATE'S ANSWER:
{user_answer}

INSTRUCTIONS:
1. Score the answer from 0 to 10 based on the evaluation criteria and the candidate's inferred level.
2. Identify specific strengths in the answer.
3. Identify specific areas for improvement.
4. Decide if a follow-up question is needed. A follow-up is needed when:
   - The answer is vague and lacks specific examples
   - The candidate mentioned something interesting that deserves exploration
   - A key aspect of the question was not addressed
   - The answer contradicts itself or raises concerns
5. If a follow-up is needed, generate a targeted follow-up question.
6. NOT every answer needs a follow-up. Only request one when genuinely warranted.{closing_instruction}

OUTPUT FORMAT:
Return ONLY a valid JSON object:
{{
    "score": 7,
    "evaluation": "Concise assessment of the answer",
    "strengths": ["Specific strength 1", "Specific strength 2"],
    "improvements": ["Specific improvement 1"],
    "needs_follow_up": true,
    "follow_up_question": "Can you elaborate on how you measured the impact?"
}}

Return ONLY the JSON. No markdown."""

        max_retries = 2
        last_error = ""

        for attempt in range(max_retries):
            try:
                await self.ai_service.initialize()
                response = await self.ai_service.send_message(
                    user_id, "Evaluator", 0,
                    [{"role": "user", "content": prompt}]
                )

                if "error" in response:
                    raise Exception(f"AI Provider Error: {response['error']}")

                content = response["content"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                evaluation = json.loads(content)

                # Save the answer
                await self.repository.save_answer(
                    session_id=session_id,
                    question_index=question_index,
                    question_text=question["text"],
                    question_type=question["type"],
                    dimension=question["dimension"],
                    metric=question["metric"],
                    user_answer=user_answer,
                    ai_evaluation=evaluation,
                    score=evaluation.get("score", 0),
                    time_taken=time_taken,
                    has_follow_up=evaluation.get("needs_follow_up", False),
                    follow_up_question=evaluation.get("follow_up_question")
                )

                return evaluation

            except json.JSONDecodeError:
                last_error = "AI returned invalid JSON for evaluation"
                continue
            except Exception as e:
                if "AI Provider Error" in str(e):
                    raise
                last_error = str(e)
                continue

        raise Exception(f"Failed to evaluate answer: {last_error}")

    async def evaluate_follow_up(self, user_id: int, session_id: int,
                                 question_index: int, follow_up_answer: str) -> dict:
        """Evaluate a follow-up answer. No recursive follow-ups."""
        session = await self.repository.get_session(session_id, user_id)
        if not session:
            raise Exception("Session not found")

        question = session["questions"][question_index]
        answers = await self.repository.get_answers(session_id)
        original_answer = next((a for a in answers if a["question_index"] == question_index), None)
        if not original_answer:
            raise Exception("Original answer not found")

        job = await self.job_repository.get_by_id(session["job_id"], user_id)
        language = session.get("language", "en")

        prompt = f"""You are evaluating a follow-up answer in a mock interview.

CONTEXT:
- Role: {job['title']} at {job['company']}
- Candidate Level: {session['inferred_level']}
- Language: Respond in the language with code "{language}"

ORIGINAL QUESTION:
{question['text']}

CANDIDATE'S ORIGINAL ANSWER:
{original_answer['user_answer']}

FOLLOW-UP QUESTION:
{original_answer.get('follow_up_question', '')}

CANDIDATE'S FOLLOW-UP ANSWER:
{follow_up_answer}

INSTRUCTIONS:
1. Evaluate the candidate's performance on this question as a WHOLE, combining their original answer and this follow-up answer.
2. Calculate a new overall score from 0 to 10 for this entire question sequence.
3. Your feedback should address how the follow-up added to or failed to improve their initial response.
4. Do NOT request another follow-up. This is the final evaluation for this question.

OUTPUT FORMAT:
Return ONLY a valid JSON object:
{{
    "score": 7,
    "evaluation": "Holistic assessment of the complete answer sequence (original + follow-up)",
    "strengths": ["Strength 1"],
    "improvements": ["Improvement 1"],
    "needs_follow_up": false,
    "follow_up_question": null
}}

Return ONLY the JSON."""

        max_retries = 2
        for attempt in range(max_retries):
            try:
                await self.ai_service.initialize()
                response = await self.ai_service.send_message(
                    user_id, "Evaluator", 0,
                    [{"role": "user", "content": prompt}]
                )

                if "error" in response:
                    raise Exception(f"AI Provider Error: {response['error']}")

                content = response["content"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                evaluation = json.loads(content)
                evaluation["needs_follow_up"] = False
                evaluation["follow_up_question"] = None

                await self.repository.save_follow_up(
                    session_id=session_id,
                    question_index=question_index,
                    follow_up_answer=follow_up_answer,
                    follow_up_evaluation=evaluation
                )

                return evaluation

            except json.JSONDecodeError:
                continue
            except Exception as e:
                if "AI Provider Error" in str(e):
                    raise
                continue

        raise Exception("Failed to evaluate follow-up answer")

    async def finish_session(self, user_id: int, session_id: int) -> dict:
        """Generate overall summary and complete the session."""
        session = await self.repository.get_session(session_id, user_id)
        if not session:
            raise Exception("Session not found")

        answers = await self.repository.get_answers(session_id)
        job = await self.job_repository.get_by_id(session["job_id"], user_id)
        language = session.get("language", "en")

        # Build Q&A summary for the AI
        qa_summary = []
        for a in answers:
            entry = {
                "question": a["question_text"],
                "type": a["question_type"],
                "dimension": a["dimension"],
                "metric": a["metric"],
                "answer": a["user_answer"],
                "score": a["score"],
                "evaluation": a["ai_evaluation"]
            }
            if a.get("has_follow_up") and a.get("follow_up_answer"):
                entry["follow_up_question"] = a.get("follow_up_question")
                entry["follow_up_answer"] = a["follow_up_answer"]
                entry["follow_up_evaluation"] = a.get("follow_up_evaluation")
            qa_summary.append(entry)

        prompt = f"""You are generating the final report for a completed mock interview session.

CONTEXT:
- Role: {job['title']} at {job['company']}
- Candidate Level: {session['inferred_level']}
- Interview Type: {session['interview_type']}
- Total Questions: {len(answers)}
- Language: Respond in the language with code "{language}"

COMPLETE Q&A DATA:
{json.dumps(qa_summary, indent=2, ensure_ascii=False)}

INSTRUCTIONS:
1. Calculate an overall score (0-100) that represents the candidate's performance.
2. Write a concise executive summary (2-3 paragraphs).
3. Identify the strongest and weakest dimensions.
4. Provide actionable recommendations for improvement.

WRITING STYLE:
- Directness: State facts directly.
- Specificity: Reference specific answers and situations from the interview.
- Active voice: Address the candidate as "You."
- Zero filler: No adverbs or vague phrases.

OUTPUT FORMAT:
Return ONLY a valid JSON object:
{{
    "overall_score": 72,
    "executive_summary": "Multi-paragraph summary",
    "strongest_dimensions": ["Dimension 1"],
    "weakest_dimensions": ["Dimension 1"],
    "key_recommendations": ["Recommendation 1", "Recommendation 2"]
}}

Return ONLY the JSON."""

        max_retries = 2
        for attempt in range(max_retries):
            try:
                await self.ai_service.initialize()
                response = await self.ai_service.send_message(
                    user_id, "Report Generator", 0,
                    [{"role": "user", "content": prompt}]
                )

                if "error" in response:
                    raise Exception(f"AI Provider Error: {response['error']}")

                content = response["content"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                summary = json.loads(content)
                overall_score = summary.get("overall_score", 0)

                await self.repository.complete_session(
                    session_id=session_id,
                    overall_score=overall_score,
                    overall_feedback=summary
                )

                return {
                    "session_id": session_id,
                    "overall_score": overall_score,
                    "summary": summary
                }

            except json.JSONDecodeError:
                continue
            except Exception as e:
                if "AI Provider Error" in str(e):
                    raise
                continue

        raise Exception("Failed to generate session summary")

    async def get_session(self, session_id: int, user_id: int) -> Optional[dict]:
        return await self.repository.get_session(session_id, user_id)

    async def get_answers(self, session_id: int) -> list[dict]:
        return await self.repository.get_answers(session_id)

    async def list_sessions(self, user_id: int, job_id: int = None) -> list[dict]:
        return await self.repository.list_sessions(user_id, job_id)
