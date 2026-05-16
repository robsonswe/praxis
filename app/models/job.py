from pydantic import BaseModel
from typing import Optional


class JobPostCreate(BaseModel):
    title: str
    company: str
    location: str = ""
    job_type: str = "full-time"
    salary: str = ""
    link: str = ""
    description: str = ""
    company_description: str = ""


class JobPost(BaseModel):
    id: Optional[int] = None
    user_id: int
    title: str
    company: str
    location: str = ""
    job_type: str = "full-time"
    salary: str = ""
    link: str = ""
    description: str = ""
    company_description: str = ""
    created_at: Optional[str] = None


class FitInsight(BaseModel):
    area: str
    description: str
    severity: str  # high, medium, low
    actionable: bool
    suggestion: Optional[str] = None


class JobAnalysis(BaseModel):
    id: Optional[int] = None
    job_id: int
    user_id: int
    overall_score: int
    technical_fit: int
    cultural_fit: int
    strengths: list[FitInsight]
    gaps: list[FitInsight]
    red_flags: list[FitInsight]
    recommendations: list[str]
    positioning_strategy: str
    analyzed_at: Optional[str] = None


class JobProfile(BaseModel):
    id: Optional[int] = None
    job_id: int
    user_id: int
    name: str
    email: str
    title: str = ""
    summary: str = ""
    location: str = ""
    years_of_experience: int = 0
    date_of_birth: str = ""
    phone: str = ""
    website: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    work_experience: list[dict] = []
    education: list[dict] = []
    certifications: list[dict] = []
    courses: list[dict] = []
    achievements: list[dict] = []
    skills: list[dict] = []
    projects: list[dict] = []
    languages: list[dict] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
