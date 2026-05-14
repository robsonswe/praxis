import json
from datetime import datetime
from typing import Optional
from app.models.job import JobAnalysis, FitInsight, JobPost
from app.repositories.job_analysis import JobAnalysisRepository
from app.repositories.job import JobRepository
from app.services.ai_service import AIService
from app.services.profile import ProfileService
from app.services.behavioral import BehavioralService

class JobAnalysisService:
    def __init__(self, 
                 repository: JobAnalysisRepository,
                 job_repository: JobRepository,
                 profile_service: ProfileService,
                 behavioral_service: BehavioralService,
                 ai_service: AIService):
        self.repository = repository
        self.job_repository = job_repository
        self.profile_service = profile_service
        self.behavioral_service = behavioral_service
        self.ai_service = ai_service

    async def get_analysis(self, job_id: int, user_id: int) -> Optional[JobAnalysis]:
        return await self.repository.get_by_job_user(job_id, user_id)

    async def generate_analysis(self, job_id: int, user_id: int) -> JobAnalysis:
        # 1. Gather Data
        job = await self.job_repository.get_by_id(job_id, user_id)
        if not job:
            raise Exception("Job not found")
        
        profile = await self.profile_service.get_profile(user_id)
        behavioral = await self.behavioral_service.get_profile(user_id)
        
        # Calculate age
        age = "Not provided"
        if profile.date_of_birth:
            try:
                dob = datetime.fromisoformat(profile.date_of_birth)
                age = (datetime.now() - dob).days // 365
            except:
                pass

        # 2. Construct AI Prompt
        user_data = {
            "name": profile.name,
            "title": profile.title,
            "summary": profile.summary,
            "years_of_experience": profile.years_of_experience,
            "age": age,
            "skills": [s.dict() for s in profile.skills],
            "experience": [e.dict() for e in profile.work_experience],
            "education": [ed.dict() for ed in profile.education],
            "certifications": [c.dict() for c in profile.certifications],
            "projects": [p.dict() for p in profile.projects],
            "behavioral_traits": [{"name": t.name, "score": t.score} for t in behavioral.core_traits] if behavioral else [],
            "operating_styles": [{"category": s.category, "label": s.label} for s in behavioral.operating_styles] if behavioral else []
        }

        job_data = {
            "title": job["title"],
            "company": job["company"],
            "description": job["description"],
            "company_description": job["company_description"]
        }

        prompt = f"""
        Perform a deep job fit analysis between the following User Profile and Job Description.
        
        USER PROFILE:
        {json.dumps(user_data, indent=2)}
        
        JOB DESCRIPTION:
        {json.dumps(job_data, indent=2)}
        
        INSTRUCTIONS:
        1. Calculate 'technical_fit' (0-100) based on hard skills, experience, projects, and education.
        2. Calculate 'cultural_fit' (0-100) based on behavioral traits, age, and company context.
        3. Identify 'strengths': areas where the user exceeds or perfectly matches requirements.
        4. Identify 'gaps': missing skills or experience. Mark critical mismatches as 'red_flags' (high severity gaps).
        5. Provide a 'positioning_strategy': how the user should pitch themselves.
        6. Provide a list of 'recommendations': specific actions to improve their chances.
        
        WRITING STYLE (STOP-SLOP PROTOCOL):
        - Directness: State facts directly. No announcements like "Here's the thing" or "It turns out."
        - No Jargon: Avoid "navigate," "unpack," "deep dive," "landscape," or "game-changer." Use handle, examine, analysis, situation.
        - Specificity: Name specific technologies/traits. No vague declaratives ("The stakes are high").
        - Active Agency: Inanimate objects don't act. "The code shows" is slop; "You can see in the code" is better.
        - Reader Perspective: Address the candidate as "You." Put them in the room with the manager.
        - Zero Filler: Kill all adverbs (really, just, deeply, truly, actually, simply, crucially).
        - Rhythm: Vary sentence lengths. Two items beat three. No em-dashes.
        - No Binary Contrasts: Avoid "Not X, but Y." State Y directly. 
        - No Rhetorical Setups: Cut "Think about it" or "Here's what I mean." Just make the point.
        - Skip the Runway: Don't tell the reader something is important; show them the specific consequence.
        
        OUTPUT FORMAT:
        You MUST return ONLY a JSON object with the following structure:
        {{
            "technical_fit": int,
            "cultural_fit": int,
            "strengths": [
                {{"area": "string", "description": "string", "severity": "high|medium|low", "actionable": bool, "suggestion": "optional string"}}
            ],
            "gaps": [
                {{"area": "string", "description": "string", "severity": "high|medium|low", "actionable": bool, "suggestion": "string"}}
            ],
            "red_flags": [
                {{"area": "string", "description": "string", "severity": "high|medium|low", "actionable": bool, "suggestion": "string"}}
            ],
            "recommendations": ["string", "string"],
            "positioning_strategy": "string"
        }}
        """

        # 3. Call AI with Retries
        max_retries = 3
        last_error = ""
        
        for attempt in range(max_retries):
            try:
                await self.ai_service.initialize()
                response = await self.ai_service.send_message(user_id, profile.name, 0, [{"role": "user", "content": prompt}])
                
                if "error" in response:
                    # Connection/Rate limit errors - these are provider level, don't retry for format
                    raise Exception(f"AI Provider Error: {response['error']}")
                
                # 4. Parse and Validate
                content = response["content"]
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                try:
                    data = json.loads(content)
                    technical_fit = data.get("technical_fit", 0)
                    cultural_fit = data.get("cultural_fit", 0)
                    overall_score = (technical_fit + cultural_fit) // 2

                    analysis = JobAnalysis(
                        job_id=job_id,
                        user_id=user_id,
                        overall_score=overall_score,
                        technical_fit=technical_fit,
                        cultural_fit=cultural_fit,
                        strengths=[FitInsight(**s) for s in data.get("strengths", [])],
                        gaps=[FitInsight(**g) for g in data.get("gaps", [])],
                        red_flags=[FitInsight(**rf) for rf in data.get("red_flags", [])],
                        recommendations=data.get("recommendations", []),
                        positioning_strategy=data.get("positioning_strategy", "")
                    )
                    
                    # 5. Save to DB
                    return await self.repository.upsert(analysis)
                    
                except json.JSONDecodeError:
                    last_error = "The AI returned an invalid JSON format"
                    continue
                except Exception as e:
                    last_error = f"Validation failed: {str(e)}"
                    continue
                    
            except Exception as e:
                if "AI Provider Error" in str(e):
                    # Immediate failure for provider issues
                    raise Exception(f"Failed to communicate with AI provider: {str(e).split(': ')[-1]}")
                last_error = str(e)
                continue

        # If we reach here, we failed all retries
        raise Exception(f"AI failed to provide a valid analysis after {max_retries} attempts. Reason: {last_error}. Suggestion: Try using a different AI model or provider in settings.")
