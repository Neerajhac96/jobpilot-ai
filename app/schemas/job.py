from pydantic import BaseModel


class JobCreate(BaseModel):
    title: str
    company: str
    location: str | None = None

    job_url: str
    source: str

    description: str | None = None
    requirements: str | None = None

    salary: str | None = None
    experience: str | None = None
    employment_type: str | None = None

    posted_date: str | None = None

class ProcessRequest(BaseModel):
    max_jobs: int = 20
