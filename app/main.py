import json
from datetime import datetime
from contextlib import asynccontextmanager

from app.agents.job_matcher import JobMatcherAgent
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from app.scheduler.job_scheduler import start_scheduler, run_job_hunt, get_scheduler_status

from app.database.database import Base, engine, get_db
from app.database.models import Candidate, Job, TailoredResume
from app.schemas.candidate import CandidateCreate, CandidatePreferencesUpdate
from app.schemas.job import JobCreate, ProcessRequest
from app.schemas.job_search import JobSearchRequest
from app.jobs.test_source import TestJobSource
from app.jobs.remotive import RemotiveJobSource
from app.services.job_service import save_job, collect_and_save_jobs
from app.services.job_processing import process_jobs_pipeline, get_ranked_jobs
from app.agents.job_analyzer import JobAnalyzerAgent
from app.agents.resume_agent import ResumeAgent
from app.services.resume_generator import generate_resume_docx
from pathlib import Path
import shutil

from fastapi import UploadFile, File

from app.services.resume_parser import (
    ResumeParserAgent,
    extract_docx_text
)


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="JobPilot AI",
    description="AI-powered job discovery and application assistant",
    version="0.1.0"
)


@app.get("/")
def root():
    return {
        "name": "JobPilot AI",
        "status": "running",
        "version": "0.1.0"
    }


from sqlalchemy import text
from app.scheduler.job_scheduler import get_scheduler_status

@app.get("/health")
def health(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
        
    scheduler_status = get_scheduler_status().get("status", "unknown")
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "scheduler": scheduler_status,
        "version": "1.0.0"
    }


@app.post("/candidate")
def create_candidate(
    candidate: CandidateCreate,
    db: Session = Depends(get_db)
):
    new_candidate = Candidate(
        name=candidate.name,
        email=candidate.email,
        phone=candidate.phone,
        location=candidate.location,
        education=candidate.education,
        skills=candidate.skills,
        experience=candidate.experience,
        projects=candidate.projects,
        certifications=candidate.certifications,
        preferred_roles=candidate.preferred_roles,
        preferred_locations=candidate.preferred_locations,
        resume_path=candidate.resume_path
    )

    db.add(new_candidate)
    db.commit()
    db.refresh(new_candidate)

    return {
        "message": "Candidate profile created",
        "candidate_id": new_candidate.id
    }


@app.post("/jobs")
def create_job(
    job: JobCreate,
    db: Session = Depends(get_db)
):
    new_job = Job(
        title=job.title,
        company=job.company,
        location=job.location,
        job_url=job.job_url,
        source=job.source,
        description=job.description,
        requirements=job.requirements,
        salary=job.salary,
        experience=job.experience,
        employment_type=job.employment_type,
        posted_date=job.posted_date
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    return {
        "message": "Job created",
        "job_id": new_job.id
    }


@app.get("/jobs")
def get_jobs(
    db: Session = Depends(get_db)
):
    jobs = db.query(Job).all()

    return jobs

@app.post("/jobs/process")
def process_jobs(req: ProcessRequest, db: Session = Depends(get_db)):
    result, error = process_jobs_pipeline(db, req.max_jobs)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    return result

@app.get("/jobs/ranked")
def ranked_jobs(min_score: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    result, error = get_ranked_jobs(db, min_score, limit)
    if error:
        raise HTTPException(status_code=400, detail=error["error"])
    return result

@app.post("/jobs/collect/test")
def collect_test_jobs(
    db: Session = Depends(get_db)
):
    collector = TestJobSource()

    jobs = collector.collect()

    created = 0
    skipped = 0

    for raw_job in jobs:

        _, is_new = save_job(
            db,
            raw_job
        )

        if is_new:
            created += 1
        else:
            skipped += 1

    return {
        "source": "test_source",
        "jobs_found": len(jobs),
        "jobs_created": created,
        "jobs_skipped": skipped
    }


@app.post("/jobs/search")
def search_jobs(
    search_req: JobSearchRequest,
    db: Session = Depends(get_db)
):
    if search_req.source == "remotive" or not search_req.source:
        collector = RemotiveJobSource()
    elif search_req.source == "test":
        collector = TestJobSource()
    else:
        raise HTTPException(status_code=400, detail="Unknown source")
        
    found, created, skipped, saved_jobs = collect_and_save_jobs(db, collector, search_req)
    
    return {
        "jobs_found": found,
        "jobs_created": created,
        "jobs_skipped": skipped,
        "source": collector.source_name,
        "jobs": saved_jobs
    }


@app.post("/jobs/{job_id}/analyze")
def analyze_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        return {
            "error": "Job not found"
        }

    description = job.description or ""
    requirements = job.requirements or ""

    full_text = f"""
Job Title:
{job.title}

Company:
{job.company}

Location:
{job.location or ""}

Job Description:
{description}

Requirements:
{requirements}

Salary:
{job.salary or ""}

Experience:
{job.experience or ""}

Employment Type:
{job.employment_type or ""}
"""

    agent = JobAnalyzerAgent()

    analysis = agent.analyze(full_text)

    job.analysis_json = json.dumps(
        analysis,
        ensure_ascii=False
    )

    db.commit()
    db.refresh(job)

    return {
        "job_id": job.id,
        "title": job.title,
        "company": job.company,
        "analysis": analysis
    }

def _do_match(job, candidate):
    job_analysis = json.loads(job.analysis_json)
    agent = JobMatcherAgent()
    result = agent.match(
        candidate=candidate,
        job=job,
        job_analysis=job_analysis
    )
    return {
        "job": {
            "id": job.id,
            "title": job.title,
            "company": job.company
        },
        "candidate": {
            "id": candidate.id,
            "name": candidate.name
        },
        "match": result
    }

@app.post("/jobs/{job_id}/match/{candidate_id}")
def match_job(
    job_id: int,
    candidate_id: int,
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return {"error": "Job not found"}

    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        return {"error": "Candidate not found"}

    if not job.analysis_json:
        return {"error": "Job has not been analyzed yet. Analyze it first."}

    return _do_match(job, candidate)


@app.post("/jobs/{job_id}/match")
def match_active_candidate(
    job_id: int,
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    candidate = db.query(Candidate).order_by(Candidate.id.desc()).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if not job.analysis_json:
        raise HTTPException(status_code=400, detail="Job has not been analyzed yet. Analyze it first.")

    return _do_match(job, candidate)


@app.get("/jobs/{job_id}/match")
def get_match_active_candidate(
    job_id: int,
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    candidate = db.query(Candidate).order_by(Candidate.id.desc()).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if not job.analysis_json:
        raise HTTPException(status_code=400, detail="Job has not been analyzed yet. Analyze it first.")

    return _do_match(job, candidate)

@app.post("/jobs/{job_id}/resume/{candidate_id}")
def tailor_resume(
    job_id: int,
    candidate_id: int,
    db: Session = Depends(get_db)
):
    job = (
        db.query(Job)
        .filter(Job.id == job_id)
        .first()
    )

    if not job:
        return {
            "error": "Job not found"
        }

    candidate = (
        db.query(Candidate)
        .filter(Candidate.id == candidate_id)
        .first()
    )

    if not candidate:
        return {
            "error": "Candidate not found"
        }

    if not job.analysis_json:
        return {
            "error": "Job must be analyzed first."
        }

    job_analysis = json.loads(
        job.analysis_json
    )

    matcher = JobMatcherAgent()

    match_result = matcher.match(
        candidate=candidate,
        job=job,
        job_analysis=job_analysis
    )

    resume_agent = ResumeAgent()

    tailored_resume = resume_agent.tailor(
        candidate=candidate,
        job=job,
        job_analysis=job_analysis,
        match_result=match_result
    )

    resume_path = generate_resume_docx(
    candidate=candidate,
    job=job,
    tailored_resume=tailored_resume
    )

    resume_record = TailoredResume(
        candidate_id=candidate.id,
        job_id=job.id,
        content_json=json.dumps(
            tailored_resume,
            ensure_ascii=False
        )
    )

    db.add(resume_record)
    db.commit()
    db.refresh(resume_record)

    return {
        "message": "Tailored resume created",
        "resume_file": resume_path,
        "resume_id": resume_record.id,
        "job": {
            "id": job.id,
            "title": job.title,
            "company": job.company
        },
        "candidate": {
            "id": candidate.id,
            "name": candidate.name
        },
        "match": match_result,
        "tailored_resume": tailored_resume
    }


@app.get("/resumes")
def get_resumes(
    db: Session = Depends(get_db)
):
    resumes = (
        db.query(TailoredResume)
        .order_by(TailoredResume.id.desc())
        .all()
    )

    results = []

    for resume in resumes:
        results.append({
            "id": resume.id,
            "candidate_id": resume.candidate_id,
            "job_id": resume.job_id,
            "created_at": resume.created_at,
            "content": json.loads(resume.content_json)
        })

    return results

@app.post("/candidate/resume")
def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename:
        return {
            "error": "No file provided"
        }

    extension = Path(file.filename).suffix.lower()

    if extension != ".docx":
        return {
            "error": "Currently only .docx resumes are supported."
        }

    original_dir = Path("data/resumes/original")
    original_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    safe_filename = Path(file.filename).name

    file_path = original_dir / safe_filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(
            file.file,
            buffer
        )

    resume_text = extract_docx_text(
        str(file_path)
    )

    parser = ResumeParserAgent()

    parsed = parser.parse(resume_text)

    candidate = (
        db.query(Candidate)
        .order_by(Candidate.id.desc())
        .first()
    )

    if candidate:
        # Update existing profile
        candidate.name = parsed.get("name", "")
        candidate.email = parsed.get("email", "")
        candidate.phone = parsed.get("phone", "")
        candidate.location = parsed.get("location", "")
        candidate.education = parsed.get("education", "")

        candidate.skills = ", ".join(
            parsed.get("skills", [])
        )

        candidate.experience = parsed.get(
            "experience",
            ""
        )

        candidate.projects = "\n".join(
            parsed.get("projects", [])
        )

        candidate.certifications = ", ".join(
            parsed.get("certifications", [])
        )

        candidate.resume_path = str(file_path)
    else:
        # Create first candidate profile
        candidate = Candidate(
            name=parsed.get("name", ""),
            email=parsed.get("email", ""),
            phone=parsed.get("phone", ""),
            location=parsed.get("location", ""),
            education=parsed.get("education", ""),
            skills=", ".join(
                parsed.get("skills", [])
            ),
            experience=parsed.get(
                "experience",
                ""
            ),
            projects="\n".join(
                parsed.get("projects", [])
            ),
            certifications=", ".join(
                parsed.get("certifications", [])
            ),
            resume_path=str(file_path),
            preferred_roles="",
            preferred_locations=""
        )
        db.add(candidate)

    db.commit()
    db.refresh(candidate)

    return {
        "message": "Resume uploaded and parsed successfully",
        "candidate_id": candidate.id,
        "resume_path": str(file_path),
        "parsed_profile": parsed
    }

@app.get("/candidate/me")
def get_active_candidate(
    db: Session = Depends(get_db)
):
    candidate = (
        db.query(Candidate)
        .order_by(Candidate.id.desc())
        .first()
    )

    if not candidate:
        raise HTTPException(status_code=404, detail="No candidate profile found")

    return {
        "id": candidate.id,
        "name": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
        "location": candidate.location,
        "education": candidate.education,
        "skills": candidate.skills,
        "experience": candidate.experience,
        "projects": candidate.projects,
        "certifications": candidate.certifications,
        "preferred_roles": candidate.preferred_roles,
        "preferred_locations": candidate.preferred_locations,
        "resume_path": candidate.resume_path
    }

@app.put("/candidate/preferences")
def update_candidate_preferences(
    preferences: CandidatePreferencesUpdate,
    db: Session = Depends(get_db)
):
    candidate = (
        db.query(Candidate)
        .order_by(Candidate.id.desc())
        .first()
    )

    if not candidate:
        raise HTTPException(status_code=404, detail="No candidate profile found")

    if preferences.preferred_roles is not None:
        candidate.preferred_roles = preferences.preferred_roles
    if preferences.preferred_locations is not None:
        candidate.preferred_locations = preferences.preferred_locations

    db.commit()
    db.refresh(candidate)

    return {
        "message": "Candidate preferences updated",
        "preferred_roles": candidate.preferred_roles,
        "preferred_locations": candidate.preferred_locations
    }

from app.database.models import Application
from app.services.application_service import prepare_application

@app.post('/jobs/{job_id}/application/prepare')
def api_prepare_application(job_id: int, db: Session = Depends(get_db)):
    app_record = prepare_application(db, job_id)
    
    return {
        'application_id': app_record.id,
        'status': app_record.status,
        'candidate_id': app_record.candidate_id,
        'job_id': app_record.job_id,
        'match_score': app_record.match_score,
        'resume_id': app_record.tailored_resume_id,
        'cover_letter': app_record.cover_letter,
        'application_answers': json.loads(app_record.application_answers_json) if app_record.application_answers_json else {}
    }

@app.get('/applications/{application_id}')
def api_get_application(application_id: int, db: Session = Depends(get_db)):
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record:
        raise HTTPException(status_code=404, detail='Application not found')
        
    return {
        'application_id': app_record.id,
        'status': app_record.status,
        'candidate_id': app_record.candidate_id,
        'job_id': app_record.job_id,
        'match_score': app_record.match_score,
        'resume_id': app_record.tailored_resume_id,
        'cover_letter': app_record.cover_letter,
        'application_answers': json.loads(app_record.application_answers_json) if app_record.application_answers_json else {}
    }

@app.get('/applications')
def api_list_applications(status: str = None, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(Application)
    if status:
        query = query.filter(Application.status == status)
    
    apps = query.order_by(Application.id.desc()).limit(limit).all()
    results = []
    for app_record in apps:
        results.append({
            'application_id': app_record.id,
            'status': app_record.status,
            'candidate_id': app_record.candidate_id,
            'job_id': app_record.job_id,
            'match_score': app_record.match_score
        })
    return results

@app.post('/applications/{application_id}/approve')
def api_approve_application(application_id: int, db: Session = Depends(get_db)):
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record:
        raise HTTPException(status_code=404, detail='Application not found')
        
    if app_record.status != 'PENDING_APPROVAL':
        raise HTTPException(status_code=400, detail='Only PENDING_APPROVAL applications can be approved')
        
    app_record.status = 'APPROVED'
    db.commit()
    db.refresh(app_record)
    
    return {
        'application_id': app_record.id,
        'status': app_record.status
    }


from app.database.models import ApplicationProfile
from app.schemas.application_profile import ApplicationProfileUpdate, ApplicationProfileResponse

@app.get('/candidate/application-profile', response_model=ApplicationProfileResponse)
def get_application_profile(db: Session = Depends(get_db)):
    candidate = db.query(Candidate).order_by(Candidate.id.desc()).first()
    if not candidate:
        raise HTTPException(status_code=404, detail='No active candidate')
        
    profile = db.query(ApplicationProfile).filter(ApplicationProfile.candidate_id == candidate.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail='Application profile not found')
        
    return profile

@app.put('/candidate/application-profile', response_model=ApplicationProfileResponse)
def update_application_profile(profile_data: ApplicationProfileUpdate, db: Session = Depends(get_db)):
    candidate = db.query(Candidate).order_by(Candidate.id.desc()).first()
    if not candidate:
        raise HTTPException(status_code=404, detail='No active candidate')
        
    profile = db.query(ApplicationProfile).filter(ApplicationProfile.candidate_id == candidate.id).first()
    
    if not profile:
        profile = ApplicationProfile(candidate_id=candidate.id)
        db.add(profile)
        
    update_data = profile_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)
        
    db.commit()
    db.refresh(profile)
    return profile


from app.browser.browser_agent import BrowserApplicationAgent
from app.database.models import ApplicationProfile, TailoredResume
import os

@app.post('/applications/{application_id}/dry-run')
def api_dry_run_application(application_id: int, test_url: str = None, db: Session = Depends(get_db)):
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record:
        raise HTTPException(status_code=404, detail='Application not found')
        
    if app_record.status != 'APPROVED':
        raise HTTPException(status_code=400, detail='Application must be APPROVED before dry-run')
        
    candidate = db.query(Candidate).filter(Candidate.id == app_record.candidate_id).first()
    job = db.query(Job).filter(Job.id == app_record.job_id).first()
    profile = db.query(ApplicationProfile).filter(ApplicationProfile.candidate_id == candidate.id).first()
    resume_record = db.query(TailoredResume).filter(TailoredResume.id == app_record.tailored_resume_id).first()
    
    if test_url:
        job.job_url = test_url
    
    resume_path = None
    if resume_record:
        expected_path = os.path.join('data', 'resumes', f'{candidate.id}_{job.id}_tailored_resume.docx')
        if os.path.exists(expected_path):
            resume_path = os.path.abspath(expected_path)
            
    agent = BrowserApplicationAgent(app_record, candidate, job, profile, resume_path)
    report = agent.run_dry_run()
    
    return report


from pydantic import BaseModel

class ConfirmSubmissionRequest(BaseModel):
    confirm: bool
    test_url: str = None

@app.post('/applications/{application_id}/confirm-submission')
def api_confirm_submission(application_id: int, req: ConfirmSubmissionRequest, db: Session = Depends(get_db)):
    app_record = db.query(Application).filter(Application.id == application_id).first()
    if not app_record:
        raise HTTPException(status_code=404, detail='Application not found')
        
    if app_record.status != 'APPROVED':
        raise HTTPException(status_code=400, detail='Application must be APPROVED before submission')
        
    if not req.confirm:
        raise HTTPException(status_code=400, detail='Explicit confirmation required')
        
    app_record.submission_confirmed_at = datetime.utcnow()
    app_record.status = 'SUBMISSION_STARTED'
    db.commit()
    db.refresh(app_record)
    
    candidate = db.query(Candidate).filter(Candidate.id == app_record.candidate_id).first()
    job = db.query(Job).filter(Job.id == app_record.job_id).first()
    
    if req.test_url:
        job.job_url = req.test_url
    profile = db.query(ApplicationProfile).filter(ApplicationProfile.candidate_id == candidate.id).first()
    resume_record = db.query(TailoredResume).filter(TailoredResume.id == app_record.tailored_resume_id).first()
    
    resume_path = None
    if resume_record:
        expected_path = os.path.join('data', 'resumes', f'{candidate.id}_{job.id}_tailored_resume.docx')
        if os.path.exists(expected_path):
            resume_path = os.path.abspath(expected_path)
            
    agent = BrowserApplicationAgent(app_record, candidate, job, profile, resume_path)
    result = agent.submit_application(db)
    
    return result

@app.get('/dashboard/stats')
def api_dashboard_stats(db: Session = Depends(get_db)):
    total_jobs = db.query(Job).count()
    analyzed_jobs = db.query(Job).filter(Job.analysis_json.isnot(None)).count()
    unanalyzed_jobs = total_jobs - analyzed_jobs
    
    strong = db.query(Application).filter(Application.recommendation == 'STRONG_MATCH').count()
    review = db.query(Application).filter(Application.recommendation == 'REVIEW').count()
    skip = db.query(Application).filter(Application.recommendation == 'SKIP').count()
    
    total_apps = db.query(Application).count()
    pending = db.query(Application).filter(Application.status == 'PENDING_APPROVAL').count()
    approved = db.query(Application).filter(Application.status == 'APPROVED').count()
    submitted = db.query(Application).filter(Application.status == 'SUBMITTED').count()
    interview = db.query(Application).filter(Application.status == 'INTERVIEW').count()
    rejected = db.query(Application).filter(Application.status == 'REJECTED').count()
    
    return {
        "jobs": {
            "total": total_jobs,
            "analyzed": analyzed_jobs,
            "unanalyzed": unanalyzed_jobs
        },
        "matches": {
            "strong": strong,
            "review": review,
            "skip": skip
        },
        "applications": {
            "total": total_apps,
            "pending_approval": pending,
            "approved": approved,
            "submitted": submitted,
            "interview": interview,
            "rejected": rejected
        }
    }


@app.post('/scheduler/run-now')
def api_scheduler_run_now():
    # APScheduler should be able to trigger the job, but we'll just run it directly synchronously
    res = run_job_hunt()
    return res

@app.get('/scheduler/status')
def api_scheduler_status():
    return get_scheduler_status()
