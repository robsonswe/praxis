from typing import Any, Optional
from app.repositories.profile import ProfileRepository
from app.models.profile import (
    ProfileBasic, WorkExperience, WorkExperienceCreate,
    Education, EducationCreate, Certification, CertificationCreate,
    Course, CourseCreate, Achievement, AchievementCreate,
    Skill, SkillCreate, Project, ProjectCreate, UserProfile,
    Language, LanguageCreate
)


def _strip_str(val: Any) -> Any:
    return val.strip() if isinstance(val, str) else val


class ProfileService:
    def __init__(self, repository: ProfileRepository):
        self.repository = repository
    
    async def get_profile(self, user_id: int) -> UserProfile | None:
        user = await self.repository.get_by_user_id(user_id)
        if not user:
            return None
        
        work_experience = await self.repository.get_work_experience(user_id)
        education = await self.repository.get_education(user_id)
        certifications = await self.repository.get_certifications(user_id)
        courses = await self.repository.get_courses(user_id)
        achievements = await self.repository.get_achievements(user_id)
        skills = await self.repository.get_skills(user_id)
        projects = await self.repository.get_projects(user_id)
        languages = await self.repository.get_languages(user_id)
        
        return UserProfile(
            id=user["id"],
            name=user["name"],
            email=user["email"],
            title=user.get("title", ""),
            summary=user.get("summary", ""),
            location=user.get("location", ""),
            years_of_experience=user.get("years_of_experience", 0),
            date_of_birth=user.get("date_of_birth", ""),
            phone=user.get("phone", ""),
            website=user.get("website", ""),
            linkedin=user.get("linkedin", ""),
            github=user.get("github", ""),
            work_experience=[WorkExperience(**w) for w in work_experience],
            education=[Education(**e) for e in education],
            certifications=[Certification(**c) for c in certifications],
            courses=[Course(**c) for c in courses],
            achievements=[Achievement(**a) for a in achievements],
            skills=[Skill(**s) for s in skills],
            projects=[Project(**p) for p in projects],
            languages=[Language(**l) for l in languages]
        )
    
    async def update_basic(self, user_id: int, basic: ProfileBasic) -> dict | None:
        return await self.repository.update_basic(
            user_id, 
            name=_strip_str(basic.name), 
            title=_strip_str(basic.title), 
            summary=_strip_str(basic.summary), 
            location=_strip_str(basic.location), 
            years_of_experience=basic.years_of_experience,
            date_of_birth=_strip_str(basic.date_of_birth),
            phone=_strip_str(basic.phone),
            website=_strip_str(basic.website),
            linkedin=_strip_str(basic.linkedin),
            github=_strip_str(basic.github)
        )
    
    async def get_work_experience(self, user_id: int) -> list[WorkExperience]:
        data = await self.repository.get_work_experience(user_id)
        return [WorkExperience(**w) for w in data]
    
    async def create_work_experience(self, user_id: int, data: WorkExperienceCreate) -> WorkExperience:
        data.experience_type = data.experience_type.strip().lower().replace("_", "-")
        result = await self.repository.create_work_experience(
            user_id, 
            _strip_str(data.company), 
            _strip_str(data.title), 
            data.experience_type, 
            _strip_str(data.location), 
            data.start_date,
            data.end_date, 
            data.current, 
            _strip_str(data.description)
        )
        return WorkExperience(**result)
    
    async def update_work_experience(self, exp_id: int, user_id: int, data: WorkExperienceCreate) -> WorkExperience | None:
        data.experience_type = data.experience_type.strip().lower().replace("_", "-")
        result = await self.repository.update_work_experience(
            exp_id, user_id, 
            _strip_str(data.company), 
            _strip_str(data.title), 
            data.experience_type, 
            _strip_str(data.location), 
            data.start_date,
            data.end_date, 
            data.current, 
            _strip_str(data.description)
        )
        if result:
            return WorkExperience(**result)
        return None

    async def delete_work_experience(self, exp_id: int, user_id: int) -> bool:
        return await self.repository.delete_work_experience(exp_id, user_id)
    
    async def get_education(self, user_id: int) -> list[Education]:
        data = await self.repository.get_education(user_id)
        return [Education(**e) for e in data]
    
    async def create_education(self, user_id: int, data: EducationCreate) -> Education:
        result = await self.repository.create_education(
            user_id, 
            _strip_str(data.institution), 
            _strip_str(data.degree), 
            _strip_str(data.field), 
            data.start_date, 
            data.end_date, 
            data.gpa
        )
        return Education(**result)
    
    async def update_education(self, edu_id: int, user_id: int, data: EducationCreate) -> Education | None:
        result = await self.repository.update_education(
            edu_id, user_id, 
            _strip_str(data.institution), 
            _strip_str(data.degree), 
            _strip_str(data.field),
            data.start_date, 
            data.end_date, 
            data.gpa
        )
        if result:
            return Education(**result)
        return None
    
    async def delete_education(self, edu_id: int, user_id: int) -> bool:
        return await self.repository.delete_education(edu_id, user_id)
    
    async def get_certifications(self, user_id: int) -> list[Certification]:
        data = await self.repository.get_certifications(user_id)
        return [Certification(**c) for c in data]
    
    async def create_certification(self, user_id: int, data: CertificationCreate) -> Certification:
        result = await self.repository.create_certification(
            user_id, 
            _strip_str(data.name), 
            _strip_str(data.issuer), 
            data.issue_date, 
            data.expiry_date, 
            _strip_str(data.credential_id), 
            _strip_str(data.url)
        )
        return Certification(**result)
    
    async def update_certification(self, cert_id: int, user_id: int, data: CertificationCreate) -> Certification | None:
        result = await self.repository.update_certification(
            cert_id, user_id, 
            _strip_str(data.name), 
            _strip_str(data.issuer), 
            data.issue_date,
            data.expiry_date, 
            _strip_str(data.credential_id), 
            _strip_str(data.url)
        )
        if result:
            return Certification(**result)
        return None
    
    async def delete_certification(self, cert_id: int, user_id: int) -> bool:
        return await self.repository.delete_certification(cert_id, user_id)
    
    async def get_courses(self, user_id: int) -> list[Course]:
        data = await self.repository.get_courses(user_id)
        return [Course(**c) for c in data]
    
    async def create_course(self, user_id: int, data: CourseCreate) -> Course:
        result = await self.repository.create_course(
            user_id, 
            _strip_str(data.name), 
            _strip_str(data.provider), 
            data.completion_date, 
            _strip_str(data.certificate_url), 
            _strip_str(data.description)
        )
        return Course(**result)
    
    async def update_course(self, course_id: int, user_id: int, data: CourseCreate) -> Course | None:
        result = await self.repository.update_course(
            course_id, user_id, 
            _strip_str(data.name), 
            _strip_str(data.provider), 
            data.completion_date,
            _strip_str(data.certificate_url), 
            _strip_str(data.description)
        )
        if result:
            return Course(**result)
        return None
    
    async def delete_course(self, course_id: int, user_id: int) -> bool:
        return await self.repository.delete_course(course_id, user_id)
    
    async def get_achievements(self, user_id: int) -> list[Achievement]:
        data = await self.repository.get_achievements(user_id)
        return [Achievement(**a) for a in data]
    
    async def create_achievement(self, user_id: int, data: AchievementCreate) -> Achievement:
        data.category = data.category.strip().lower()
        result = await self.repository.create_achievement(
            user_id, 
            _strip_str(data.title), 
            data.category, 
            _strip_str(data.description), 
            data.date, 
            _strip_str(data.organization)
        )
        return Achievement(**result)
    
    async def update_achievement(self, ach_id: int, user_id: int, data: AchievementCreate) -> Achievement | None:
        data.category = data.category.strip().lower()
        result = await self.repository.update_achievement(
            ach_id, user_id, 
            _strip_str(data.title), 
            data.category, 
            _strip_str(data.description), 
            data.date, 
            _strip_str(data.organization)
        )
        if result:
            return Achievement(**result)
        return None
    
    async def delete_achievement(self, ach_id: int, user_id: int) -> bool:
        return await self.repository.delete_achievement(ach_id, user_id)
    
    async def get_skills(self, user_id: int) -> list[Skill]:
        data = await self.repository.get_skills(user_id)
        return [Skill(**s) for s in data]
    
    async def create_skill(self, user_id: int, data: SkillCreate) -> Skill:
        data.category = data.category.strip().lower()
        result = await self.repository.create_skill(
            user_id, 
            _strip_str(data.name), 
            data.category, 
            data.proficiency, 
            data.years_of_experience
        )
        return Skill(**result)
    
    async def update_skill(self, skill_id: int, user_id: int, data: SkillCreate) -> Skill | None:
        data.category = data.category.strip().lower()
        result = await self.repository.update_skill(
            skill_id, user_id, 
            _strip_str(data.name), 
            data.category, 
            data.proficiency, 
            data.years_of_experience
        )
        if result:
            return Skill(**result)
        return None
    
    async def delete_skill(self, skill_id: int, user_id: int) -> bool:
        return await self.repository.delete_skill(skill_id, user_id)
    
    async def get_projects(self, user_id: int) -> list[Project]:
        data = await self.repository.get_projects(user_id)
        return [Project(**p) for p in data]
    
    async def create_project(self, user_id: int, data: ProjectCreate) -> Project:
        result = await self.repository.create_project(
            user_id, 
            _strip_str(data.name), 
            _strip_str(data.description), 
            _strip_str(data.role),
            [_strip_str(t) for t in data.technologies], 
            [_strip_str(o) for o in data.outcomes], 
            data.start_date, 
            data.end_date
        )
        return Project(**result)
    
    async def update_project(self, proj_id: int, user_id: int, data: ProjectCreate) -> Project | None:
        result = await self.repository.update_project(
            proj_id, user_id, 
            _strip_str(data.name), 
            _strip_str(data.description), 
            _strip_str(data.role),
            [_strip_str(t) for t in data.technologies], 
            [_strip_str(o) for o in data.outcomes], 
            data.start_date, 
            data.end_date
        )
        if result:
            return Project(**result)
        return None
    
    async def delete_project(self, proj_id: int, user_id: int) -> bool:
        return await self.repository.delete_project(proj_id, user_id)

    async def get_languages(self, user_id: int) -> list[Language]:
        data = await self.repository.get_languages(user_id)
        return [Language(**l) for l in data]

    async def create_language(self, user_id: int, data: LanguageCreate) -> Language:
        result = await self.repository.create_language(
            user_id, 
            _strip_str(data.name), 
            data.level
        )
        return Language(**result)

    async def delete_language(self, lang_id: int, user_id: int) -> bool:
        return await self.repository.delete_language(lang_id, user_id)

    async def check_completeness(self, user_id: int, context: str = "general") -> dict:
        """
        Returns structured missing fields: {'essential': [], 'recommended': []}
        Logic: 
        - Essential: If no work experience, requires Summary, Skills, and Education.
        - Recommended (Fit Analysis): Behavioral Profile.
        """
        profile = await self.get_profile(user_id)
        if not profile:
            return {"essential": ["Basic profile info"], "recommended": []}
        
        essential = []
        recommended = []

        # Logic: Experience overrides basic bare minimums
        if not profile.work_experience:
            if not profile.summary or not profile.summary.strip():
                essential.append("Professional Summary")
            if not profile.skills:
                essential.append("Skills")
            if not profile.education:
                essential.append("Education")
            
        # Fit Analysis specific "nice-to-have"
        if context == "fit_analysis":
            from app.services.behavioral import BehavioralService
            behavioral_service = BehavioralService()
            behavioral = await behavioral_service.get_profile(user_id)
            if not behavioral:
                recommended.append("Behavioral Assessment")
            
        return {"essential": essential, "recommended": recommended}