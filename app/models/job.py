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
