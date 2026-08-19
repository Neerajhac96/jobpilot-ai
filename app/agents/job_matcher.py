import json

from app.ai.groq_client import GroqClient
from app.services.matching import calculate_match


class JobMatcherAgent:

    def __init__(self):
        self.ai = GroqClient()

    def match(
        self,
        candidate,
        job,
        job_analysis: dict,
        include_explanation: bool = True
    ) -> dict:

        score_result = calculate_match(
            candidate=candidate,
            job_analysis=job_analysis,
            job_title=job.title,
            job_location=job.location
        )

        if not include_explanation:
            return {
                **score_result,
                "ai_analysis": None
            }

        prompt = f"""
You are a professional job matching assistant.

Evaluate this candidate against this job.

CANDIDATE:

Name:
{candidate.name}

Education:
{candidate.education or ""}

Skills:
{candidate.skills or ""}

Experience:
{candidate.experience or ""}

Projects:
{candidate.projects or ""}

Preferred Roles:
{candidate.preferred_roles or ""}

Preferred Locations:
{candidate.preferred_locations or ""}


JOB:

Title:
{job.title}

Company:
{job.company}

Location:
{job.location or ""}

AI Job Analysis:
{json.dumps(job_analysis, ensure_ascii=False)}


CALCULATED MATCH:

{json.dumps(score_result, ensure_ascii=False)}


Return ONLY valid JSON:

{{
    "summary": "",
    "strengths": [],
    "missing_skills": [],
    "concerns": [],
    "recommendation_reason": ""
}}

Rules:

- Do not change the calculated match score.
- Do not invent candidate skills.
- Do not invent job requirements.
- Keep the explanation concise.
"""

        response = self.ai.generate(prompt)

        try:
            explanation = json.loads(response)

        except json.JSONDecodeError:
            explanation = {
                "summary": response,
                "strengths": [],
                "missing_skills": score_result["skills"]["missing"],
                "concerns": [],
                "recommendation_reason": ""
            }

        return {
            **score_result,
            "ai_analysis": explanation
        }
