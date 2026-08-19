import json
from sqlalchemy.orm import Session
from app.database.models import Job, Candidate
from app.agents.job_analyzer import JobAnalyzerAgent
from app.agents.job_matcher import JobMatcherAgent
from app.services.matching import normalize
import groq

def pre_filter_jobs(candidate: Candidate, jobs: list[Job]):
    accepted = []
    rejected = []
    
    pref_roles = [normalize(r) for r in (candidate.preferred_roles or "").split(",") if r.strip()]
    
    for job in jobs:
        job_title_norm = normalize(job.title)
        
        reject_reason = None
        if pref_roles:
            match_found = False
            for role in pref_roles:
                role_words = set(role.split())
                title_words = set(job_title_norm.split())
                if role_words.intersection(title_words) or role in job_title_norm:
                    match_found = True
                    break
            if not match_found:
                reject_reason = "Job title does not match any preferred roles"
        
        if reject_reason:
            rejected.append({"job": job, "reason": reject_reason})
        else:
            accepted.append(job)
            
    return accepted, rejected

def process_jobs_pipeline(db: Session, max_jobs: int):
    candidate = db.query(Candidate).order_by(Candidate.id.desc()).first()
    if not candidate:
        return None, {"error": "No active candidate found"}
        
    unanalyzed_jobs = db.query(Job).filter(Job.analysis_json.is_(None)).limit(max_jobs).all()
    jobs_considered = len(unanalyzed_jobs)
    
    accepted_jobs, rejected_jobs = pre_filter_jobs(candidate, unanalyzed_jobs)
    
    analyzer = JobAnalyzerAgent()
    analyzed_count = 0
    failed_count = 0
    
    for job in accepted_jobs:
        try:
            analysis = analyzer.analyze(job)
            job.analysis_json = json.dumps(analysis, ensure_ascii=False)
            db.commit()
            analyzed_count += 1
        except groq.APIStatusError as e:
            print(f"Permanent API error for job {job.id}: {e}")
            db.rollback()
            job.analysis_json = json.dumps({"status": "failed", "reason": "APIStatusError", "details": str(e)})
            db.commit()
            failed_count += 1
        except Exception as e:
            print(f"Failed to analyze job {job.id}: {e}")
            db.rollback()
            job.analysis_json = json.dumps({"status": "failed", "reason": "GeneralError", "details": str(e)})
            db.commit()
            failed_count += 1
            
    analyzed_jobs = db.query(Job).filter(Job.analysis_json.is_not(None)).all()
    matcher = JobMatcherAgent()
    ranked_jobs = []
    
    for job in analyzed_jobs:
        try:
            job_analysis = json.loads(job.analysis_json)
            if job_analysis.get("status") == "failed":
                continue
                
            match_result = matcher.match(candidate=candidate, job=job, job_analysis=job_analysis, include_explanation=False)
            
            ranked_jobs.append({
                "job_id": job.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "source": job.source,
                "job_url": job.job_url,
                "match_score": match_result.get("match_score", 0),
                "recommendation": match_result.get("recommendation", "SKIP"),
                "matched_skills": match_result.get("skills", {}).get("matched", []),
                "missing_skills": match_result.get("skills", {}).get("missing", []),
                "experience_score": match_result.get("experience_score", 0),
                "role_score": match_result.get("role_score", 0),
                "location_score": match_result.get("location_score", 0),
                "education_score": match_result.get("education_score", 0)
            })
        except Exception as e:
            print(f"Match failed for job {job.id}: {e}")
            
    ranked_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    
    return {
        "processing": {
            "jobs_considered": jobs_considered,
            "jobs_pre_filtered": len(rejected_jobs),
            "jobs_analyzed": analyzed_count,
            "jobs_failed": failed_count
        },
        "ranked_jobs": ranked_jobs
    }, None

def get_ranked_jobs(db: Session, min_score: int, limit: int):
    candidate = db.query(Candidate).order_by(Candidate.id.desc()).first()
    if not candidate:
        return None, {"error": "No active candidate found"}
        
    analyzed_jobs = db.query(Job).filter(Job.analysis_json.is_not(None)).all()
    if not analyzed_jobs:
        return None, {"error": "No analyzed jobs found"}
        
    matcher = JobMatcherAgent()
    ranked_jobs = []
    
    for job in analyzed_jobs:
        try:
            job_analysis = json.loads(job.analysis_json)
            if job_analysis.get("status") == "failed":
                continue
                
            match_result = matcher.match(candidate=candidate, job=job, job_analysis=job_analysis, include_explanation=False)
            score = match_result.get("match_score", 0)
            
            if score >= min_score:
                ranked_jobs.append({
                    "job_id": job.id,
                    "title": job.title,
                    "company": job.company,
                    "location": job.location,
                    "source": job.source,
                    "job_url": job.job_url,
                    "match_score": score,
                    "recommendation": match_result.get("recommendation", "SKIP"),
                    "matched_skills": match_result.get("skills", {}).get("matched", []),
                    "missing_skills": match_result.get("skills", {}).get("missing", []),
                    "experience_score": match_result.get("experience_score", 0),
                    "role_score": match_result.get("role_score", 0),
                    "location_score": match_result.get("location_score", 0),
                    "education_score": match_result.get("education_score", 0)
                })
        except Exception as e:
            print(f"Match failed for job {job.id}: {e}")
            
    ranked_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    return ranked_jobs[:limit], None
