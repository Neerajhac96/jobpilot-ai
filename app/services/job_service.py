from sqlalchemy.orm import Session

from app.database.models import Job
from app.jobs.collector import RawJob


def save_job(db: Session, raw_job: RawJob):

    existing_job = (
        db.query(Job)
        .filter(Job.job_url == raw_job.job_url)
        .first()
    )

    if existing_job:
        return existing_job, False

    job = Job(
        title=raw_job.title,
        company=raw_job.company,
        location=raw_job.location,
        job_url=raw_job.job_url,
        source=raw_job.source,
        description=raw_job.description,
        requirements=raw_job.requirements,
        salary=raw_job.salary,
        experience=raw_job.experience,
        employment_type=raw_job.employment_type,
        posted_date=raw_job.posted_date
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    return job, True


def collect_and_save_jobs(db, collector, search_params):
    raw_jobs = collector.collect(search_params)
    
    created = 0
    skipped = 0
    saved_jobs = []
    
    for raw_job in raw_jobs:
        job, is_new = save_job(db, raw_job)
        if is_new:
            created += 1
        else:
            skipped += 1
        saved_jobs.append({
            'id': job.id,
            'title': job.title,
            'company': job.company,
            'job_url': job.job_url,
            'source': job.source
        })
            
    return len(raw_jobs), created, skipped, saved_jobs

