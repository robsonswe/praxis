from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class BehavioralResponse(BaseModel):
    question_id: int
    selected_option: str # 'A', 'B', 'C', 'D'

class BehavioralAssessment(BaseModel):
    responses: List[BehavioralResponse]

class CoreTrait(BaseModel):
    name: str
    score: float # 0 to 100
    description: str

class OperatingStyle(BaseModel):
    category: str
    label: str
    description: str

class StrategicInsight(BaseModel):
    title: str
    text: str
    type: str # 'positive', 'neutral', 'warning'

class BehavioralProfile(BaseModel):
    user_id: int
    core_traits: List[CoreTrait]
    operating_styles: List[OperatingStyle]
    strategic_insights: List[StrategicInsight]
    created_at: datetime
    updated_at: datetime
