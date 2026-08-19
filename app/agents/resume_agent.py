import json

from app.ai.groq_client import GroqClient


class ResumeAgent:

    def __init__(self):
        self.ai = GroqClient()

    def tailor(
        self,
        candidate,
        job,
        job_analysis: dict,
        match_result: dict
    ) -> dict:

        prompt = f"""
You are an expert ATS resume tailoring agent.

Your task is to tailor a candidate's existing resume information
for a specific job.

STRICT RULES:

1. Never invent skills.
2. Never invent work experience.
3. Never invent companies.
4. Never invent projects.
5. Never invent certifications.
6. Never invent education.
7. Never invent achievements or numbers.
8. Do not add technologies that the candidate has not provided.
9. You may rewrite existing information to make it clearer.
10. You may reorder skills based on relevance.
11. You may emphasize relevant projects.
12. Keep all claims truthful.

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

Certifications:
{candidate.certifications or ""}


JOB:

Title:
{job.title}

Company:
{job.company}

Location:
{job.location or ""}

JOB ANALYSIS:

{json.dumps(job_analysis, ensure_ascii=False)}

MATCH RESULT:

{json.dumps(match_result, ensure_ascii=False)}


Return ONLY valid JSON using this exact structure:

{{
    "professional_summary": "",
    "skills": [],
    "experience": [],
    "projects": [],
    "education": [],
    "certifications": [],
    "keywords_emphasized": []
}}

The professional summary must only use information that is
supported by the candidate data.

For experience and projects, rewrite existing information only.
Do not create new experiences or projects.

For skills, prioritize skills relevant to the job, but only
use skills present in the candidate profile.
"""

        response = self.ai.generate(prompt)

        try:
            return json.loads(response)

        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Resume Agent returned invalid JSON: {response}"
            ) from exc
