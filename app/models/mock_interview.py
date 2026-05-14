from pydantic import BaseModel
from typing import Optional


class MockQuestion(BaseModel):
    index: int
    type: str  # 'behavioral' or 'technical'
    dimension: str
    metric: str
    text: str
    evaluation_criteria: str


class MockAnswerEvaluation(BaseModel):
    score: int  # 0-10
    evaluation: str
    strengths: list[str]
    improvements: list[str]
    needs_follow_up: bool
    follow_up_question: Optional[str] = None


class MockSessionCreate(BaseModel):
    job_id: int
    interview_type: str  # 'behavioral', 'technical', 'mixed'
    response_mode: str   # 'text', 'voice'
    time_per_question: int  # seconds
    language: str = "en"


class MockSessionSummary(BaseModel):
    overall_score: int
    executive_summary: str
    strongest_dimensions: list[str]
    weakest_dimensions: list[str]
    key_recommendations: list[str]


class MockSession(BaseModel):
    id: Optional[int] = None
    user_id: int
    job_id: int
    interview_type: str
    response_mode: str
    time_per_question: int
    language: str = "en"
    status: str = "in_progress"
    questions: list[MockQuestion] = []
    inferred_level: str = ""
    overall_score: Optional[int] = None
    overall_feedback: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class MockAnswer(BaseModel):
    id: Optional[int] = None
    session_id: int
    question_index: int
    question_text: str
    question_type: str
    dimension: str
    metric: str
    user_answer: str
    ai_evaluation: Optional[MockAnswerEvaluation] = None
    score: int = 0
    time_taken: Optional[int] = None
    has_follow_up: bool = False
    follow_up_question: Optional[str] = None
    follow_up_answer: Optional[str] = None
    follow_up_evaluation: Optional[MockAnswerEvaluation] = None
