import json
from app.ai.groq_client import GroqClient
from app.database.models import Candidate, Job

class ApplicationPreparationAgent:

    def __init__(self):
        self.ai = GroqClient()

    def prepare_application(
        self,
        candidate: Candidate,
        job: Job,
        job_analysis: dict,
        match_result: dict,
        application_profile = None
    ) -> dict:

        profile_facts = ""
        if application_profile:
            profile_facts = f"""
APPLICATION PROFILE (KNOWN DEFAULTS):
Notice Period: {application_profile.notice_period or 'Unknown'}
Work Authorization: {application_profile.work_authorization or 'Unknown'}
Location Preference: {application_profile.location_preference or 'Unknown'}
Salary Expectation: {application_profile.salary_expectation or 'Unknown'}
Willing to Relocate: {application_profile.willing_to_relocate or 'Unknown'}
Default Phone: {application_profile.default_phone or 'Unknown'}
Default Email: {application_profile.default_email or 'Unknown'}
Additional Notes: {application_profile.additional_notes or ''}
"""

        prompt = f"""
You are an expert career coach and application assistant.

Prepare an application package for the candidate applying to this job.

CANDIDATE FACT SHEET:
Name: {candidate.name}
Location: {candidate.location or ''}
Education: {candidate.education or ''}
Skills: {candidate.skills or ''}
Experience: {candidate.experience or ''}
Projects: {candidate.projects or ''}
{profile_facts}

JOB DESCRIPTION:
Title: {job.title}
Company: {job.company}
Location: {job.location or ''}

JOB ANALYSIS:
{json.dumps(job_analysis, ensure_ascii=False)}

MATCH RESULT:
Score: {match_result.get('match_score', 0)}
Matched Skills: {', '.join(match_result.get('skills', {}).get('matched', []))}
Missing Skills: {', '.join(match_result.get('skills', {}).get('missing', []))}

Your task is to return ONLY a valid JSON object containing:
1. "cover_letter": A concise, tailored cover letter.
2. "application_answers": A dictionary of common application questions to their answers based ONLY on the provided candidate facts and APPLICATION PROFILE.

Required keys in "application_answers":
- "Why are you interested in this role?"
- "Why should we hire you?"
- "Relevant experience"
- "Notice period"
- "Location preference"
- "Work authorization"
- "Salary expectations"

CRITICAL RULES:
- If you know the answer from the candidate facts OR the application profile, generate the answer using that exact information.
- If the answer requires facts you DO NOT know (e.g. Notice period or Salary expectation when listed as 'Unknown'), you MUST output exactly "USER_INPUT_REQUIRED".
- NEVER invent information. Do not invent years of experience, achievements, or legal status.
- Keep the cover letter professional, short, and focused on the matched skills.

Output ONLY valid JSON matching this schema:
{{
    "cover_letter": "string",
    "application_answers": {{
        "question_string": "answer_string or USER_INPUT_REQUIRED"
    }}
}}
"""
        response = self.ai.generate(prompt, json_mode=True)
        try:
            return json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError(f"AI returned invalid JSON: {response}") from exc
