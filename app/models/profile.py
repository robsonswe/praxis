from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProfileBasic(BaseModel):
    name: str = ""
    title: str = ""
    summary: str = ""
    location: str = ""
    years_of_experience: int = 0


class WorkExperienceCreate(BaseModel):
    company: str
    title: str
    location: str = ""
    start_date: str
    end_date: Optional[str] = None
    current: bool = False
    description: str = ""


class WorkExperience(BaseModel):
    id: Optional[int] = None
    user_id: int
    company: str
    title: str
    location: str = ""
    start_date: str
    end_date: Optional[str] = None
    current: bool = False
    description: str = ""


class EducationCreate(BaseModel):
    institution: str
    degree: str
    field: str
    start_date: str
    end_date: str
    gpa: Optional[float] = None


class Education(BaseModel):
    id: Optional[int] = None
    user_id: int
    institution: str
    degree: str
    field: str
    start_date: str
    end_date: str
    gpa: Optional[float] = None


class CertificationCreate(BaseModel):
    name: str
    issuer: str
    issue_date: str
    expiry_date: Optional[str] = None
    credential_id: Optional[str] = None
    url: Optional[str] = None


class Certification(BaseModel):
    id: Optional[int] = None
    user_id: int
    name: str
    issuer: str
    issue_date: str
    expiry_date: Optional[str] = None
    credential_id: Optional[str] = None
    url: Optional[str] = None


class CourseCreate(BaseModel):
    name: str
    provider: str
    completion_date: str
    certificate_url: Optional[str] = None
    description: Optional[str] = None


class Course(BaseModel):
    id: Optional[int] = None
    user_id: int
    name: str
    provider: str
    completion_date: str
    certificate_url: Optional[str] = None
    description: Optional[str] = None


class AchievementCreate(BaseModel):
    title: str
    category: str
    description: str = ""
    date: str
    organization: Optional[str] = None


class Achievement(BaseModel):
    id: Optional[int] = None
    user_id: int
    title: str
    category: str
    description: str = ""
    date: str
    organization: Optional[str] = None


class SkillCreate(BaseModel):
    name: str
    category: str
    proficiency: int = 3
    years_of_experience: Optional[int] = None


class Skill(BaseModel):
    id: Optional[int] = None
    user_id: int
    name: str
    category: str
    proficiency: int = 3
    years_of_experience: Optional[int] = None


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    role: str = ""
    technologies: list[str] = []
    outcomes: list[str] = []
    start_date: str
    end_date: Optional[str] = None


class Project(BaseModel):
    id: Optional[int] = None
    user_id: int
    name: str
    description: str = ""
    role: str = ""
    technologies: list[str] = []
    outcomes: list[str] = []
    start_date: str
    end_date: Optional[str] = None


class UserProfile(BaseModel):
    id: int
    name: str
    email: str
    title: str = ""
    summary: str = ""
    location: str = ""
    years_of_experience: int = 0
    work_experience: list[WorkExperience] = []
    education: list[Education] = []
    certifications: list[Certification] = []
    courses: list[Course] = []
    achievements: list[Achievement] = []
    skills: list[Skill] = []
    projects: list[Project] = []