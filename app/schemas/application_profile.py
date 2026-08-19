from pydantic import BaseModel
from typing import Optional

class ApplicationProfileUpdate(BaseModel):
    notice_period: Optional[str] = None
    work_authorization: Optional[str] = None
    location_preference: Optional[str] = None
    salary_expectation: Optional[str] = None
    willing_to_relocate: Optional[str] = None
    default_phone: Optional[str] = None
    default_email: Optional[str] = None
    additional_notes: Optional[str] = None

class ApplicationProfileResponse(ApplicationProfileUpdate):
    id: int
    candidate_id: int

    class Config:
        from_attributes = True
