from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from datetime import datetime

from app.database.database import Base


class Candidate(Base):
    __tablename__ = "candidate"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False)
    phone = Column(String(30))

    location = Column(String(150))

    education = Column(Text)
    skills = Column(Text)
    experience = Column(Text)
    projects = Column(Text)
    certifications = Column(Text)

    preferred_roles = Column(Text)
    preferred_locations = Column(Text)

    resume_path = Column(String(500))


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(200), nullable=False)
    company = Column(String(200), nullable=False)
    location = Column(String(200))

    job_url = Column(String(1000), nullable=False)
    source = Column(String(100))

    description = Column(Text)
    requirements = Column(Text)

    salary = Column(String(200))
    experience = Column(String(100))
    employment_type = Column(String(100))

    posted_date = Column(String(100))

    analysis_json = Column(Text)


class TailoredResume(Base):
    __tablename__ = "tailored_resumes"

    id = Column(Integer, primary_key=True, index=True)

    candidate_id = Column(
        Integer,
        ForeignKey("candidate.id"),
        nullable=False
    )

    job_id = Column(
        Integer,
        ForeignKey("jobs.id"),
        nullable=False
    )

    content_json = Column(Text, nullable=False)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class Application(Base):
    __tablename__ = 'applications'

    id = Column(Integer, primary_key=True, index=True)

    candidate_id = Column(Integer, ForeignKey('candidate.id'), nullable=False)
    job_id = Column(Integer, ForeignKey('jobs.id'), nullable=False)
    tailored_resume_id = Column(Integer, ForeignKey('tailored_resumes.id'), nullable=True)

    status = Column(String(50), nullable=False, default='PREPARED')
    match_score = Column(Integer)
    recommendation = Column(String(50))

    cover_letter = Column(Text)
    application_answers_json = Column(Text)
    notes = Column(Text)

    submission_confirmed_at = Column(DateTime, nullable=True)
    submission_started_at = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    submission_result = Column(Text, nullable=True)
    submission_error = Column(Text, nullable=True)
    submitted_url = Column(String(1000), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ApplicationProfile(Base):
    __tablename__ = 'application_profiles'

    id = Column(Integer, primary_key=True, index=True)

    candidate_id = Column(Integer, ForeignKey('candidate.id'), nullable=False, unique=True)
    
    notice_period = Column(String(200))
    work_authorization = Column(String(200))
    location_preference = Column(String(200))
    salary_expectation = Column(String(200))
    willing_to_relocate = Column(String(50))
    
    default_phone = Column(String(50))
    default_email = Column(String(150))
    
    additional_notes = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
