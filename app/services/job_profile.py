import json
import logging
from typing import Optional
from app.models.job import JobProfile
from app.models.profile import UserProfile
from app.repositories.job_profile import JobProfileRepository
from app.repositories.job import JobRepository
from app.services.ai_service import AIService
from app.services.profile import ProfileService


# ──────────────────────────────────────────────────────────────────────────────
# Logging Configuration
# ──────────────────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ──────────────────────────────────────────────────────────────────────────────
# Prompt constants — kept out of the method so they are easy to iterate on
# without touching business logic.
# ──────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a senior technical recruiter and career coach. You tailor resumes
by making existing evidence legible to a specific role. You never fabricate.
You never inflate. When a candidate's background is thin, you write a thin
but honest resume — because a dishonest one that makes it through ATS will
fail at the interview and cost the candidate more than being filtered out.
"""

_TAILORING_PROMPT = """\
## YOUR TASK

Tailor the USER PROFILE below to the JOB DESCRIPTION below.
Return a JSON object with the exact same schema as the input profile.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER PROFILE:
{profile_json}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JOB DESCRIPTION:
{job_json}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## WHAT YOU MAY TOUCH

Only the following fields:
  - `summary` (top-level string)
  - `description` inside each `work_experience` item
  - `description` inside each `projects` item
  - The `languages` list (see Rule 4 below)
  - The `skills` list (reorder to put most relevant first; do not add or remove)
  - Which items stay vs. get removed from any list field

You MUST NOT touch: name, email, phone, location, website, linkedin, github,
company, title, institution, degree, field, issuer, credential_id, url,
start_date, end_date, current, gpa, years_of_experience, date_of_birth,
or any other field not listed above.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## RULE 1 — FIDELITY: NEVER FABRICATE OR INFLATE

There are two kinds of dishonesty in resume writing. Both are forbidden.

TYPE A — FABRICATION: Adding things that do not exist.
  - Adding a skill, tool, or technology not already present in the profile
  - Inventing a certification, course, award, or project
  - Adding a language the user has not listed
  - Claiming the candidate did something they did not do

TYPE B — INFLATION: Making real things sound like something they are not.
  This is the more common failure. It happens when you take an honest
  description and dress it in vocabulary that implies greater technical
  depth, greater authority, or greater seniority than the source text supports.

  Concrete examples of inflation that are FORBIDDEN:
  - Source says "used ERP system to enter tax data" →
    FORBIDDEN: "Implemented business rules in ERP systems"
    FORBIDDEN: "Mapped tax logic into institutional software"
    CORRECT:   "Organized tax records in the company's ERP system"

  - Source says "checked calculations for accuracy" →
    FORBIDDEN: "Modeled structured data to support compliance requirements"
    FORBIDDEN: "Managed data sets and business logic"
    CORRECT:   "Verified tax calculations against applicable regulations"

  - Source says "prepared and filed regulatory declarations" →
    FORBIDDEN: "Developed logical structures for corporate software"
    FORBIDDEN: "Ensured data consistency across business-critical workflows"
    CORRECT:   "Prepared and submitted tax filings to government agencies"

The test: could a candidate, sitting in an interview, defend every verb and
noun in the description as literally accurate? If not, rewrite it until
they could.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## RULE 2 — CROSS-DOMAIN EXPERIENCE

When a work experience entry is in a different domain from the target job
(e.g., accounting internships on a software engineering application), apply
these constraints strictly:

DO NOT transfer vocabulary across domains.
  Using accounting software as an end user is not the same as implementing
  systems, modeling data, or developing logic. These verbs belong to the
  person who built the software — not to the person who used it.

  The domain boundary is the system boundary. If the candidate operated
  inside a system, they do not get verbs that belong to the people who
  built the system.

DO identify genuine transferable signals and name them honestly.
  Cross-domain experience can carry real value. Extract it, but name it
  for what it is:
  - Attention to detail and rule compliance → "Verified tax calculations
    against fiscal regulations, flagging discrepancies for correction"
  - Working with structured data → "Organized client fiscal records in
    the company's ERP, ensuring entries matched source documents"
  - Documentation and reporting → "Prepared monthly tax filings and
    submitted them to federal agencies ahead of regulatory deadlines"

  These are honest. They signal rigour, accuracy, and procedural discipline
  — which do transfer across domains. Do not over-claim beyond this.

DO acknowledge the career transition context in the summary (see Rule 7).
  The work experience descriptions should not try to silently bridge the
  domain gap. The summary is where the transition is framed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## RULE 3 — VERB AUTHORITY MUST MATCH ACTUAL SENIORITY

Every verb choice implies a level of authority. Match the verb to what the
candidate actually did at their actual level.

INTERN or ASSISTANT — allowed verbs:
  verified, reviewed, organized, prepared, filed, documented, calculated,
  reported, checked, recorded, assisted, supported, processed, entered,
  compiled, flagged, submitted, tracked

JUNIOR (writing code, building things) — additionally allowed:
  built, wrote, implemented (only when actually writing code), tested,
  fixed, contributed, developed (only when actually developing software),
  created, debugged, refactored

MID / SENIOR — additionally allowed:
  led, designed, architected, managed (people or systems they owned),
  owned, scaled, defined, established, hired, mentored

NEVER use mid/senior verbs for intern-level roles, even if you are
tailoring for a senior target position. The experience description must
reflect what the candidate did at that time — not the seniority of the
role they are applying to now.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## RULE 4 — PRUNING

Removing irrelevant items is your primary tailoring tool.

Remove an item from any list when:
  - It has no plausible relevance to the target role or company
  - Its presence would dilute the signal-to-noise ratio for a recruiter in
    this domain

Keep an item when:
  - It demonstrates a skill, domain, or behaviour the JD references
  - It provides context that makes another kept item more credible
  - It is the only evidence of a required or desirable capability

When in doubt about a borderline item, keep it. Only remove with confidence.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## RULE 5 — LANGUAGES SECTION

Languages are only high-signal if they change what the candidate can do in
this specific role. Apply this filter:

KEEP a language entry when at least one of the following is true:
  - The JD mentions multilingual communication, specific regions, or
    customer-facing work in a language the user speaks
  - The company is international and the language affects day-to-day
    collaboration (e.g. distributed teams, documentation in that language)
  - The proficiency is C1/C2/Native and the language is not the assumed
    default for that role and market

REMOVE a language entry when:
  - It is A1/A2 — this signals communication risk, not an asset
  - The role is a local IC role with no stated international scope
  - Keeping it adds noise without changing what the candidate can do

If you keep a language entry, mention its practical relevance in the
`summary` rather than relying on the standalone section to do the work. Example:
"Communicates technical decisions with distributed teams in English and
Portuguese" is stronger than a bare "English — C2" entry.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## RULE 6 — ATS KEYWORD STRATEGY

ATS systems rank resumes by keyword matching. Exact-phrase matches dominate.

KEYWORD MIRRORING
  - Use the exact job title from the JD in the summary when it accurately
    describes the candidate. "Backend Engineer" not "Server-Side Developer".
  - Use both full form and acronym on first use: "CI/CD (Continuous
    Integration and Delivery)", "SEO (Search Engine Optimization)".
  - Use the same tool names the JD uses. If the JD says "Postgres", do not
    write "PostgreSQL" exclusively — include the exact form used in the JD.

KEYWORD DENSITY
  - Each primary required skill: 2–3 occurrences across the whole document
    (summary + experience). More than 3 reads as stuffing and modern AI-powered
    ATS may flag it.
  - Secondary skills: once, in context.

KEYWORD PLACEMENT
  - Summary is parsed first and weighted highest.
  - Most recent work experience is weighted second.
  - Skills in descriptions are captured by the parser's skills inventory.

Keywords must sit inside grammatically honest sentences. Do not force a
keyword into a description that does not genuinely support it.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## RULE 7 — WRITING STYLE

### STAR for early-career and career-transition candidates

The candidate may have little or no professional experience in the target
domain. This is common for career changers, students, and bootcamp graduates.
Do not try to hide this. The summary is where you frame it; the experience
descriptions must stay honest.

For internships and non-technical roles:
  - Lead with what the candidate literally did (verified, organized, prepared)
  - Add scope or volume where it exists: "across 40+ client company files",
    "for a team of 8 auditors", "covering 3 fiscal years of records"
  - If a number exists in the source text, use it. Do not invent one.
  - If no number exists, describe the context instead: "in a government
    institution processing electoral data" tells a reader something real.
  - Stop there. Do not invent a result that is not stated.

For self-taught skills and courses (the actual source of tech evidence):
  - The courses and skills sections carry the technical credibility.
  - Do not smuggle technical claims into work experience descriptions to
    compensate for the absence of tech work experience.
  - Example: if the candidate took a Linux course, that belongs in the
    courses section — not inserted into a description of an accounting role.

### Verb and tone rules

WRITE LIKE THIS:
  - Concrete verb + specific object: "Verified tax withholding calculations
    for 30+ client files" not "Ensured data quality"
  - Short sentences for actions, slightly longer for context
  - Two items beat three in a list

DO NOT WRITE LIKE THIS:
  - Adverbs (-ly words): "successfully", "significantly", "consistently"
  - Jargon noise: "leverage", "synergy", "ecosystem", "game-changer",
    "deep dive", "navigate challenges", "passionate"
  - Throat-clearing openers: "Responsible for", "Tasked with", "Worked on",
    "Helped to", "Assisted in", "Contributed to" — lead with the verb
  - False agency on inanimate things: "the system became more accurate" →
    "identified and corrected data entry errors in the payroll module"
  - Vague declaratives: "Improved data quality" — name the specific action
  - Passive voice: "data was validated" → "validated payroll data against
    source documents"
  - Performative adjectives: "passionate", "driven", "enthusiastic" —
    these are claims. Every recruiter ignores them.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## RULE 8 — SUMMARY FIELD

The summary is parsed first by ATS and read first by humans. It must do
three things in 2–4 sentences:

1. NAME THE TRANSITION (when relevant). If the candidate is pivoting from
   a different field, say it plainly. Recruiters will see the accounting
   internships. A summary that pretends they are software experience is
   not credible. A summary that frames the pivot honestly is.
   Example: "Computer Science student transitioning from 2 years of
   accounting work into [target role]. [Specific tech skills from courses
   and self-study.] [One transferable signal from prior work.]"

2. FRONT-LOAD THE JD KEYWORDS. Mirror the exact job title. Name the 3–4
   skills most central to this specific JD. Put them in the first sentence.

3. ANCHOR WITH ONE CONCRETE SIGNAL. Not a trait — a fact. Course completed,
   system used, language spoken, institution worked at, quantified scope.

Do not open with "Experienced [title]" if the candidate has no experience
in that domain. That is a lie the recruiter will spot in 5 seconds when
they read the work history. Write what is true and frame it well instead.
Do not use the word "passionate".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## OUTPUT FORMAT

Return ONLY a valid JSON object that matches the exact structure of the input
USER PROFILE. No markdown fences. No explanation. No preamble. No trailing
text after the closing brace.
"""

_FEEDBACK_ADDENDUM = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## USER FEEDBACK — APPLY THESE ADJUSTMENTS

{feedback}

Apply the feedback above while keeping all other rules intact. Fidelity
rules still apply: do not fabricate and do not inflate.
"""


class JobProfileService:
    def __init__(self,
                 repository: JobProfileRepository,
                 job_repository: JobRepository,
                 profile_service: ProfileService,
                 ai_service: AIService):
        self.repository = repository
        self.job_repository = job_repository
        self.profile_service = profile_service
        self.ai_service = ai_service

    async def get_job_profile(self, job_id: int, user_id: int) -> Optional[JobProfile]:
        return await self.repository.get_by_job_user(job_id, user_id)

    def _prepare_profile_data(self, profile: UserProfile) -> dict:
        return {
            "name": profile.name,
            "email": profile.email,
            "title": profile.title,
            "summary": profile.summary,
            "location": profile.location,
            "years_of_experience": profile.years_of_experience,
            "date_of_birth": profile.date_of_birth,
            "phone": profile.phone,
            "website": profile.website,
            "linkedin": profile.linkedin,
            "github": profile.github,
            "work_experience": [w.dict() for w in profile.work_experience],
            "education": [e.dict() for e in profile.education],
            "certifications": [c.dict() for c in profile.certifications],
            "courses": [c.dict() for c in profile.courses],
            "achievements": [a.dict() for a in profile.achievements],
            "skills": [s.dict() for s in profile.skills],
            "projects": [p.dict() for p in profile.projects],
            "languages": [l.dict() for l in profile.languages],
        }

    def _build_prompt(
        self,
        base_profile_data: dict,
        job_data: dict,
        feedback: Optional[str],
    ) -> str:
        prompt = _TAILORING_PROMPT.format(
            profile_json=json.dumps(base_profile_data, indent=2),
            job_json=json.dumps(job_data, indent=2),
        )
        if feedback:
            prompt += _FEEDBACK_ADDENDUM.format(feedback=feedback)
        return prompt

    @staticmethod
    def _parse_ai_response(content: str) -> dict:
        """
        Strip optional markdown fences and parse JSON.
        Raises json.JSONDecodeError on malformed output.
        """
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        return json.loads(content.strip())

    async def generate_tailored_profile(
        self,
        job_id: int,
        user_id: int,
        feedback: Optional[str] = None,
    ) -> JobProfile:
        logger.info(f"Generating tailored profile for user {user_id} and job {job_id}")
        job = await self.job_repository.get_by_id(job_id, user_id)
        if not job:
            logger.error(f"Job {job_id} not found for user {user_id}")
            raise Exception("Job not found")

        # When feedback is provided and a previous tailored version exists,
        # iterate on that version rather than the raw profile so the user's
        # prior adjustments are preserved.
        existing = await self.get_job_profile(job_id, user_id)
        if existing and feedback:
            logger.info("Iterating on existing tailored profile with feedback")
            base_profile_data = existing.dict()
        else:
            logger.info("Generating new tailored profile from base profile")
            profile = await self.profile_service.get_profile(user_id)
            if not profile:
                logger.error(f"Profile not found for user {user_id}")
                raise Exception("Profile not found.")
            base_profile_data = self._prepare_profile_data(profile)

        job_data = {
            "title": job["title"],
            "company": job["company"],
            "description": job["description"],
        }

        full_prompt = f"{_SYSTEM_PROMPT}\n\n{self._build_prompt(base_profile_data, job_data, feedback)}"

        try:
            await self.ai_service.initialize()
            response = await self.ai_service.send_message(
                user_id,
                base_profile_data.get("name", "User"),
                0,
                [
                    {"role": "user", "content": full_prompt},
                ],
            )
        except Exception as e:
            logger.exception("AI service call failed")
            raise Exception(f"AI Service Error: {str(e)}")

        if "error" in response:
            logger.error(f"AI response error: {response['error']}")
            raise Exception(f"AI Error: {response['error']}")

        try:
            tailored = self._parse_ai_response(response["content"])
            logger.info("AI response parsed successfully")
        except Exception as e:
            logger.exception("Failed to parse AI response")
            raise Exception(f"Failed to parse AI response: {str(e)}")

        try:
            jp = JobProfile(job_id=job_id, user_id=user_id, **tailored)
            return await self.repository.upsert(jp)
        except Exception as e:
            logger.exception("Failed to save JobProfile")
            raise Exception(f"Persistence error: {str(e)}")

    async def save_job_profile(self, jp: JobProfile) -> JobProfile:
        return await self.repository.upsert(jp)

    async def delete_job_profile(self, job_id: int, user_id: int):
        await self.repository.delete_by_job(job_id, user_id)
