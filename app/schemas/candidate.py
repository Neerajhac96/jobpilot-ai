from pydantic import BaseModel


class CandidateCreate(BaseModel):
    name: str
    email: str
    phone: str | None = None

    location: str | None = None
    education: str | None = None
    skills: str | None = None
    experience: str | None = None
    projects: str | None = None
    certifications: str | None = None

    preferred_roles: str | None = None
    preferred_locations: str | None = None

    resume_path: str | None = None

class CandidatePreferencesUpdate(BaseModel):
    preferred_roles: str | None = None
    preferred_locations: str | None = None
