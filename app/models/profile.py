from typing import Any, Optional, Self, Literal
from pydantic import BaseModel, Field, EmailStr, model_validator, field_validator
from datetime import datetime
import re


def validate_date_format(value: str) -> str:
    # Validates YYYY-MM or YYYY-MM-DD
    if not re.match(r'^\d{4}-\d{1,2}(-\d{1,2})?$', value):
        raise ValueError("Date must be in YYYY-MM or YYYY-MM-DD format")
    return value


def validate_url(v: Optional[str]) -> Optional[str]:
    if v and not re.match(r'^https?://[^\s/$.?#].[^\s]*$', v, re.IGNORECASE):
        raise ValueError("Invalid URL format")
    return v


class ProfileBasic(BaseModel):
    name: str = Field(..., min_length=1)
    email: EmailStr
    title: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1)
    years_of_experience: int = Field(0, ge=0)
    date_of_birth: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=1)
    website: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None

    @field_validator('date_of_birth')
    @classmethod
    def validate_dob(cls, v: str) -> str:
        return validate_date_format(v)
    
    @field_validator('website', 'linkedin', 'github')
    @classmethod
    def validate_urls(cls, v: Optional[str]) -> Optional[str]:
        return validate_url(v)


class WorkExperienceCreate(BaseModel):
    company: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    experience_type: Literal['full-time', 'part-time', 'contract', 'freelance', 'internship', 'volunteer']
    location: Optional[str] = None
    start_date: str = Field(..., min_length=1)
    end_date: Optional[str] = None
    current: bool = False
    description: str = ""

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_dates(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return validate_date_format(v)
        return v

    @model_validator(mode='after')
    def validate_date_logic(self) -> Self:
        if self.end_date:
            self.current = False
        elif not self.current:
            if not self.end_date:
                raise ValueError("end_date must be provided if currently working is false")
        return self


class WorkExperience(WorkExperienceCreate):
    id: Optional[int] = None
    user_id: int


class EducationCreate(BaseModel):
    institution: str = Field(..., min_length=1)
    degree: str = Field(..., min_length=1)
    field: str = Field(..., min_length=1)
    start_date: str = Field(..., min_length=1)
    end_date: Optional[str] = None
    gpa: Optional[float] = Field(None, ge=0.0, le=4.0)

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_dates(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return validate_date_format(v)
        return v


class Education(EducationCreate):
    id: Optional[int] = None
    user_id: int


class CertificationCreate(BaseModel):
    name: str = Field(..., min_length=1)
    issuer: str = Field(..., min_length=1)
    issue_date: str = Field(..., min_length=1)
    expiry_date: Optional[str] = None
    credential_id: Optional[str] = None
    url: Optional[str] = None

    @field_validator('issue_date', 'expiry_date')
    @classmethod
    def validate_dates(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return validate_date_format(v)
        return v
    
    @field_validator('url')
    @classmethod
    def validate_url_field(cls, v: Optional[str]) -> Optional[str]:
        return validate_url(v)


class Certification(CertificationCreate):
    id: Optional[int] = None
    user_id: int


class CourseCreate(BaseModel):
    name: str = Field(..., min_length=1)
    provider: str = Field(..., min_length=1)
    completion_date: str = Field(..., min_length=1)
    certificate_url: Optional[str] = None
    description: Optional[str] = None

    @field_validator('completion_date')
    @classmethod
    def validate_dates(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return validate_date_format(v)
        return v
    
    @field_validator('certificate_url')
    @classmethod
    def validate_url_field(cls, v: Optional[str]) -> Optional[str]:
        return validate_url(v)


class Course(CourseCreate):
    id: Optional[int] = None
    user_id: int


class AchievementCreate(BaseModel):
    title: str = Field(..., min_length=1)
    category: Literal['promotion', 'hackathon', 'scholarship', 'competition', 'award', 'other']
    description: str = Field(..., min_length=1)
    date: str = Field(..., min_length=1)
    organization: Optional[str] = None

    @field_validator('date')
    @classmethod
    def validate_dates(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return validate_date_format(v)
        return v


class Achievement(AchievementCreate):
    id: Optional[int] = None
    user_id: int
class SkillCreate(BaseModel):
    name: str = Field(..., min_length=1)
    category: Literal['technical', 'domain']
    proficiency: int = Field(3, ge=1, le=5)
    years_of_experience: Optional[int] = Field(None, ge=0)


class Skill(SkillCreate):
    id: Optional[int] = None
    user_id: int


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    role: str = ""
    technologies: list[str] = []
    outcomes: list[str] = []
    start_date: str = Field(..., min_length=1)
    end_date: Optional[str] = None

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_dates(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return validate_date_format(v)
        return v

    @field_validator('technologies', 'outcomes', mode='before')
    @classmethod
    def split_str(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            if not v.strip():
                return []
            return [part.strip() for part in v.split(',')]
        return v or []

    @model_validator(mode='after')
    def validate_outcomes(self) -> Self:
        if not self.outcomes:
            raise ValueError("At least one outcome must be provided")
        return self


class Project(ProjectCreate):
    id: Optional[int] = None
    user_id: int


class UserProfile(BaseModel):
    id: int
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
    work_experience: list[WorkExperience] = []
    education: list[Education] = []
    certifications: list[Certification] = []
    courses: list[Course] = []
    achievements: list[Achievement] = []
    skills: list[Skill] = []
    projects: list[Project] = []