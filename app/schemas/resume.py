from pydantic import BaseModel


class ParsedResume(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    education: str = ""
    skills: list[str] = []
    experience: str = ""
    projects: list[str] = []
    certifications: list[str] = []
