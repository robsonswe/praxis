from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: Optional[int] = None
    name: str = ""
    email: str = ""
    title: str = ""
    summary: str = ""
    location: str = ""
    years_of_experience: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "title": self.title,
            "summary": self.summary,
            "location": self.location,
            "years_of_experience": self.years_of_experience,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


@dataclass
class ChatSession:
    id: Optional[int] = None
    user_id: int = 0
    title: str = ""
    created_at: Optional[str] = None
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "created_at": self.created_at
        }


@dataclass
class Message:
    id: Optional[int] = None
    session_id: int = 0
    role: str = "user"  # "user" or "assistant"
    content: str = ""
    created_at: Optional[str] = None
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at
        }


from app.models.profile import (
    ProfileBasic,
    WorkExperience,
    WorkExperienceCreate,
    Education,
    EducationCreate,
    Certification,
    CertificationCreate,
    Course,
    CourseCreate,
    Achievement,
    AchievementCreate,
    Skill,
    SkillCreate,
    Project,
    ProjectCreate,
    UserProfile,
)

__all__ = [
    "User",
    "ChatSession",
    "Message",
    "ProfileBasic",
    "WorkExperience",
    "WorkExperienceCreate",
    "Education",
    "EducationCreate",
    "Certification",
    "CertificationCreate",
    "Course",
    "CourseCreate",
    "Achievement",
    "AchievementCreate",
    "Skill",
    "SkillCreate",
    "Project",
    "ProjectCreate",
    "UserProfile",
]