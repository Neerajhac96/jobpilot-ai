import os
import json
from datetime import datetime, timedelta
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database.database import SessionLocal
from app.database.models import Candidate, Job, Application
from app.services.job_service import collect_and_save_jobs
from app.schemas.job_search import JobSearchRequest
from app.agents.job_analyzer import JobAnalyzerAgent
from app.agents.job_matcher import JobMatcherAgent

# Logger setup
log_dir = os.path.join("data", "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(log_dir, "scheduler.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("scheduler")

scheduler = BackgroundScheduler()

# State
scheduler_state = {
    "status": "idle",
    "last_run": None,
    "next_run": None,
    "last_result": None
}

def run_job_hunt():
    logger.info("Starting run_job_hunt()")
    scheduler_state["status"] = "running"
    
    db = SessionLocal()
    try:
        candidate = db.query(Candidate).order_by(Candidate.id.desc()).first()
        if not candidate:
            logger.warning("No candidate found. Aborting job hunt.")
            scheduler_state["status"] = "idle"
            return {"error": "No candidate found"}
            
        # 1. Search
        locations = [l.strip() for l in settings.JOB_SEARCH_LOCATIONS.split(",")]
        
        jobs_found = 0
        jobs_created = 0
        
        req = JobSearchRequest(
            keywords=settings.JOB_SEARCH_KEYWORDS,
            locations=locations,
            remote=settings.JOB_SEARCH_REMOTE,
            max_results=settings.JOB_SEARCH_MAX_RESULTS,
            posted_within_days=settings.JOB_SEARCH_POSTED_WITHIN_DAYS
        )
        
        from app.jobs.remotive import RemotiveJobSource
        collector = RemotiveJobSource()
        
        # This function internally handles deduplication and saving
        total_found, created, skipped, saved_jobs = collect_and_save_jobs(db, collector, req)
        
        jobs_found = total_found
        jobs_created = created
        
        # 2. Analyze new jobs
        unanalyzed_jobs = db.query(Job).filter(Job.analysis_json.is_(None)).all()
        analyzer = JobAnalyzerAgent()
        
        jobs_analyzed = 0
        for job in unanalyzed_jobs:
            try:
                analysis = analyzer.analyze(job)
                job.analysis_json = json.dumps(analysis)
                jobs_analyzed += 1
            except Exception as e:
                logger.error(f"Failed to analyze job {job.id}: {e}")
                
        db.commit()
        
        # 3. Match jobs (In-memory, do not prepare applications)
        matcher = JobMatcherAgent()
        strong_matches = 0
        
        analyzed_unmatched = db.query(Job).filter(
            Job.analysis_json.isnot(None),
            ~Job.id.in_(db.query(Application.job_id))
        ).all()
        
        for job in analyzed_unmatched:
            try:
                analysis_dict = json.loads(job.analysis_json)
                result = matcher.match(candidate, job, analysis_dict, include_explanation=False)
                if result.get("recommendation") == "STRONG_MATCH":
                    strong_matches += 1
            except Exception as e:
                logger.error(f"Failed to match job {job.id}: {e}")
                
        # db.commit() not needed as we didn't mutate any records in matching phase
        
        result = {
            "status": "completed",
            "jobs_found": jobs_found,
            "jobs_created": jobs_created,
            "jobs_analyzed": jobs_analyzed,
            "strong_matches": strong_matches
        }
        
        scheduler_state["last_result"] = result
        scheduler_state["last_run"] = datetime.now().isoformat()
        scheduler_state["status"] = "idle"
        
        logger.info(f"Finished job hunt: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        scheduler_state["status"] = "idle"
        return {"error": str(e)}
    finally:
        db.close()

def start_scheduler():
    interval_minutes = settings.JOB_SEARCH_INTERVAL_MINUTES
    scheduler.add_job(run_job_hunt, 'interval', minutes=interval_minutes, id='job_hunt')
    scheduler.start()
    
    # Update next_run
    job = scheduler.get_job('job_hunt')
    if job:
        scheduler_state["next_run"] = job.next_run_time.isoformat() if job.next_run_time else None

def get_scheduler_status():
    job = scheduler.get_job('job_hunt')
    if job:
        scheduler_state["next_run"] = job.next_run_time.isoformat() if job.next_run_time else None
        
    return scheduler_state
