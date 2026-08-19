import json

from app.ai.groq_client import GroqClient


class JobAnalyzerAgent:

    def __init__(self):
        self.ai = GroqClient()

    def analyze(self, job) -> dict:
        description = job.description or ""
        requirements = job.requirements or ""
        
        full_text = (
            f"Job Title: {job.title}\n"
            f"Company: {job.company}\n"
            f"Location: {job.location or ''}\n"
            f"Job Description: {description}\n"
            f"Requirements: {requirements}\n"
            f"Salary: {job.salary or ''}\n"
            f"Experience: {job.experience or ''}\n"
            f"Employment Type: {job.employment_type or ''}"
        )

        if not full_text.strip():
            raise ValueError(
                "Job text is empty. "
                "Cannot analyze an empty job."
            )
            
        # Truncate to avoid permanent 413 "Request too large" TPM limits on Groq free tier
        # Limit max characters to 10000 to ensure we stay well within the ~4000 prompt token budget
        MAX_CHARS = 10000
        if len(full_text) > MAX_CHARS:
            full_text = full_text[:MAX_CHARS] + "\n...[TRUNCATED]"

        prompt = f"""
You are a professional job description analysis agent.

Analyze the job description below.

Extract only information that is actually present.

Return ONLY valid JSON.

Required structure:

{{
    "job_category": "",
    "required_skills": [],
    "preferred_skills": [],
    "experience_required": "",
    "education_required": "",
    "location": "",
    "employment_type": "",
    "salary": "",
    "responsibilities": [],
    "keywords": []
}}

Rules:

- Never invent information.
- If something is not mentioned, use an empty string or empty list.
- Keep skills as individual items.
- Separate required skills from preferred skills.
- Keep responsibilities concise.
- Extract technologies, programming languages,
  databases, BI tools, cloud tools and frameworks.
- Return valid JSON only.

JOB DESCRIPTION:

{full_text}
"""

        response = self.ai.generate(prompt, json_mode=True)

        try:
            return json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"AI returned invalid JSON: {response}"
            ) from exc
