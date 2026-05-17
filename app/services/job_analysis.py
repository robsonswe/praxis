import json
import logging
from datetime import datetime, date
from typing import Optional
from app.models.job import JobAnalysis, FitInsight
from app.repositories.job_analysis import JobAnalysisRepository
from app.repositories.job import JobRepository
from app.repositories.job_profile import JobProfileRepository
from app.services.ai_service import AIService
from app.services.profile import ProfileService
from app.services.behavioral import BehavioralService

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Prompt Constants
# ──────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a brutally honest, highly analytical technical recruiter and hiring manager.
Your job is to evaluate a candidate's actual fit for a specific role.
You do not sugarcoat. You do not hallucinate competencies. You ruthlessly 
separate what a candidate has actually *done* from what they *claim*, and you 
delineate between using software and building it.
"""

_ANALYSIS_PROMPT = """\
## YOUR TASK

Perform a deep, brutally honest job fit analysis between the CANDIDATE PROFILE and the JOB DESCRIPTION.
Return a JSON object matching the exact schema requested.

TODAY'S DATE: {today}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CANDIDATE PROFILE (Source: {profile_source}):
{profile_json}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JOB DESCRIPTION:
{job_json}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## RULE 1 — RECENCY AND TIME DECAY (THE "OLD" RULE)
Technology and relevance move fast. 
- Experience from 4+ years ago carries a heavy discount. 
- If experience from 4+ years ago is in a DIFFERENT DOMAIN (e.g., accounting, retail, support), it has ZERO relevance to technical fit today. Do not try to bridge old, unrelated domains to current tech roles.
- The `years_of_experience` field represents their time in the *target domain*. Judge them based on this, not their total chronological working years.

## RULE 2 — CROSS-DOMAIN REALITY (NO INFLATION)
Never conflate using a system with building one.
- If they used an ERP, they did not "build enterprise software." 
- Soft skills (accuracy, stakeholder management) from past careers contribute to Cultural Fit, but they contribute ZERO to Technical Fit.

## RULE 3 — SENIORITY ALIGNMENT & VERB AUTHORITY
Assess actual proven authority, not just tool familiarity.
- Look at their verbs: Did they "assist" and "verify", or did they "architect" and "own"?
- If the JD requires a Mid/Senior Engineer, and the user only has Junior experience or Bootcamp projects, this is a HIGH SEVERITY RED FLAG. Call out the gap explicitly.
- Do not pretend a 6-month internship prepares someone for independent delivery.

## RULE 4 — SCORING REALISM (0-100)
Be harsh but fair. 
- 0-30: Completely unqualified. Major missing core skills.
- 31-60: Stretch role. Missing years of experience or key architectural skills.
- 61-80: Solid match. Hits core requirements but has minor tool or domain gaps.
- 81-100: Unicorn (Extremely rare). 
Do not automatically give 80+ just because they list the right keywords. They must have the matching experience timeline and authority.

## RULE 5 — BEHAVIORAL STRICTNESS
Evaluate the behavioral traits provided in the profile.
- ONLY consider traits with a score of >= 70 as actual strengths.
- ONLY map those >= 70 traits as a "strength" if the JD explicitly or implicitly requires that behavior (e.g., "Resilience" for a high-paced startup).
- If a trait scores < 40 and the JD requires it, flag it as a gap.

## RULE 6 — ACTIONABLE RECOMMENDATIONS & POSITIONING
- Recommendations must be specific technical or tactical actions. 
  * BAD: "Improve your Python skills."
  * GOOD: "Build a backend CRUD app using FastAPI and pytest to prove you can handle the API requirements of this role."
- Positioning Strategy: Tell the candidate exactly how to frame their background in an interview to survive their weaknesses (gaps) and highlight their real strengths.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## WRITING STYLE (STOP-SLOP PROTOCOL)

- Directness: State facts directly. No "Here's the thing" or "Overall."
- No Jargon: Avoid "navigate," "unpack," "deep dive," "landscape," or "game-changer."
- Specificity: Name specific technologies/traits. No vague declaratives ("The stakes are high").
- Active Agency: "The code shows" is slop; "You can see in the code" is better.
- Reader Perspective: Address the candidate as "You." Put them in the room with the manager.
- Zero Filler: Kill all adverbs (really, just, deeply, truly, actually, simply, crucially).
- No Binary Contrasts: Avoid "Not X, but Y." State Y directly. 
- Skip the Runway: Don't tell the reader something is important; show them the specific consequence.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## OUTPUT FORMAT

You MUST return ONLY a JSON object with the following structure:
{{
    "technical_fit": int, // 0-100
    "cultural_fit": int, // 0-100
    "strengths": [
        {{"area": "string", "description": "string", "severity": "low", "actionable": false, "suggestion": "string"}}
    ],
    "gaps": [
        {{"area": "string", "description": "string", "severity": "medium|high", "actionable": true, "suggestion": "string"}}
    ],
    "red_flags": [
        {{"area": "string", "description": "string", "severity": "high", "actionable": true, "suggestion": "string"}}
    ],
    "recommendations": ["string", "string"],
    "positioning_strategy": "string"
}}
"""

class JobAnalysisService:
    def __init__(self, 
                 repository: JobAnalysisRepository,
                 job_repository: JobRepository,
                 profile_service: ProfileService,
                 job_profile_repository: JobProfileRepository,
                 behavioral_service: BehavioralService,
                 ai_service: AIService):
        self.repository = repository
        self.job_repository = job_repository
        self.profile_service = profile_service
        self.job_profile_repository = job_profile_repository
        self.behavioral_service = behavioral_service
        self.ai_service = ai_service

    async def get_analysis(self, job_id: int, user_id: int) -> Optional[JobAnalysis]:
        return await self.repository.get_by_job_user(job_id, user_id)

    async def generate_analysis(self, job_id: int, user_id: int) -> JobAnalysis:
        # 1. Gather Job Data
        job = await self.job_repository.get_by_id(job_id, user_id)
        if not job:
            raise Exception("Job not found")
        
        # 2. Gather Profile Data (Prefer Tailored JobProfile, fallback to raw UserProfile)
        job_profile = await self.job_profile_repository.get_by_job_user(job_id, user_id)
        profile_source = ""
        user_data = {}

        if job_profile:
            logger.info(f"Using TAILORED JobProfile for analysis of job {job_id}")
            profile_source = "TAILORED_JOB_PROFILE (Irrelevant/Old experience has already been pruned)"
            user_data = {
                "name": job_profile.name,
                "title": job_profile.title,
                "summary": job_profile.summary,
                "years_of_experience": job_profile.years_of_experience,
                "skills": job_profile.skills,
                "experience": job_profile.work_experience,
                "education": job_profile.education,
                "certifications": job_profile.certifications,
                "projects": job_profile.projects,
                "languages": job_profile.languages
            }
        else:
            logger.info(f"Using RAW UserProfile for analysis of job {job_id} (No tailored profile found)")
            profile = await self.profile_service.get_profile(user_id)
            if not profile:
                raise Exception("User profile not found")
            profile_source = "RAW_USER_PROFILE (Contains full history, must be strictly filtered by relevance and age)"
            user_data = {
                "name": profile.name,
                "title": profile.title,
                "summary": profile.summary,
                "years_of_experience": profile.years_of_experience,
                "skills": [s.dict() for s in profile.skills],
                "experience": [e.dict() for e in profile.work_experience],
                "education": [ed.dict() for ed in profile.education],
                "certifications": [c.dict() for c in profile.certifications],
                "projects": [p.dict() for p in profile.projects],
                "languages": [l.dict() for l in profile.languages]
            }

        # 3. Gather Behavioral Data
        behavioral = await self.behavioral_service.get_profile(user_id)
        if behavioral:
            user_data["behavioral_traits"] = [{"name": t.name, "score": t.score} for t in behavioral.core_traits]
            user_data["operating_styles"] = [{"category": s.category, "label": s.label} for s in behavioral.operating_styles]
        else:
            user_data["behavioral_traits"] = []
            user_data["operating_styles"] = []

        # 4. Construct AI Prompt
        job_data = {
            "title": job["title"],
            "company": job["company"],
            "description": job["description"],
            "company_description": job["company_description"]
        }

        prompt = _ANALYSIS_PROMPT.format(
            today=date.today().isoformat(),
            profile_source=profile_source,
            profile_json=json.dumps(user_data, indent=2),
            job_json=json.dumps(job_data, indent=2)
        )
        
        full_prompt = f"{_SYSTEM_PROMPT}\n\n{prompt}"

        # 5. Call AI with Retries
        max_retries = 3
        last_error = ""
        
        for attempt in range(max_retries):
            try:
                await self.ai_service.initialize()
                response = await self.ai_service.send_message(
                    user_id, 
                    user_data["name"], 
                    0, 
                    [{"role": "user", "content": full_prompt}]
                )
                
                if "error" in response:
                    raise Exception(f"AI Provider Error: {response['error']}")
                
                # 6. Parse and Validate
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
                    
                    # 7. Save to DB
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
        raise Exception(f"AI failed to provide a valid analysis after {max_retries} attempts. Reason: {last_error}.")