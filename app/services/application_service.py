import json
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.database.models import Job, Candidate, TailoredResume, Application
from app.agents.job_matcher import JobMatcherAgent
from app.agents.resume_agent import ResumeAgent
from app.agents.application_agent import ApplicationPreparationAgent
from app.services.resume_generator import generate_resume_docx

def prepare_application(db: Session, job_id: int, candidate_id: int = None):
    # 1. Resolve candidate
    if candidate_id:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    else:
        candidate = db.query(Candidate).order_by(Candidate.id.desc()).first()
        
    if not candidate:
        raise HTTPException(status_code=404, detail="No candidate found")
        
    # 2. Validate job exists
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    # 3. Validate job has analysis_json
    if not job.analysis_json:
        raise HTTPException(status_code=400, detail="Job has not been analyzed yet")
        
    try:
        job_analysis = json.loads(job.analysis_json)
        if job_analysis.get("status") == "failed":
            raise HTTPException(status_code=400, detail="Job analysis failed permanently for this job")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Job has invalid analysis JSON")
        
    # 4. Get deterministic match score
    matcher = JobMatcherAgent()
    match_result = matcher.match(
        candidate=candidate, 
        job=job, 
        job_analysis=job_analysis, 
        include_explanation=False
    )
    
    # 5 & 6. Reuse or generate tailored resume
    resume_record = db.query(TailoredResume).filter(
        TailoredResume.candidate_id == candidate.id,
        TailoredResume.job_id == job.id
    ).first()
    
    if not resume_record:
        resume_agent = ResumeAgent()
        tailored_resume_content = resume_agent.tailor(
            candidate=candidate,
            job=job,
            job_analysis=job_analysis,
            match_result=match_result
        )
        
        # We don't absolutely need the file path here, but generation function expects it
        generate_resume_docx(
            candidate=candidate,
            job=job,
            tailored_resume=tailored_resume_content
        )
        
        resume_record = TailoredResume(
            candidate_id=candidate.id,
            job_id=job.id,
            content_json=json.dumps(tailored_resume_content, ensure_ascii=False)
        )
        db.add(resume_record)
        db.commit()
        db.refresh(resume_record)
        
    # Check if application already exists
    application = db.query(Application).filter(
        Application.candidate_id == candidate.id,
        Application.job_id == job.id
    ).first()
    
    if application:
        return application
        
    # Fetch Application Profile
    from app.database.models import ApplicationProfile
    profile = db.query(ApplicationProfile).filter(ApplicationProfile.candidate_id == candidate.id).first()
        
    # 7. Run ApplicationPreparationAgent
    app_agent = ApplicationPreparationAgent()
    app_package = app_agent.prepare_application(
        candidate=candidate,
        job=job,
        job_analysis=job_analysis,
        match_result=match_result,
        application_profile=profile
    )
    
    # 8. Create Application record
    application = Application(
        candidate_id=candidate.id,
        job_id=job.id,
        tailored_resume_id=resume_record.id,
        status="PENDING_APPROVAL",
        match_score=match_result.get("match_score"),
        recommendation=match_result.get("recommendation"),
        cover_letter=app_package.get("cover_letter"),
        application_answers_json=json.dumps(app_package.get("application_answers", {}), ensure_ascii=False)
    )
    
    db.add(application)
    db.commit()
    db.refresh(application)
    
    return application
