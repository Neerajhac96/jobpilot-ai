import requests
from app.jobs.collector import JobSource, RawJob

class RemotiveJobSource(JobSource):
    source_name = 'remotive'

    def collect(self, search_params) -> list[RawJob]:
        url = 'https://remotive.com/api/remote-jobs'
        params = {}
        
        if search_params.keywords:
            params['search'] = search_params.keywords
        
        limit = search_params.max_results if search_params.max_results else 20
        params['limit'] = limit

        try:
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            jobs = data.get('jobs', [])
        except Exception as e:
            print(f'Remotive API error: {e}')
            return []
            
        raw_jobs = []
        for j in jobs:
            raw_jobs.append(RawJob(
                title=j.get('title', ''),
                company=j.get('company_name', ''),
                location=j.get('candidate_required_location'),
                job_url=j.get('url', ''),
                source=self.source_name,
                description=j.get('description', ''),
                requirements=', '.join(j.get('tags', [])),
                salary=j.get('salary'),
                experience=None,
                employment_type=j.get('job_type'),
                posted_date=j.get('publication_date')
            ))
            
        return raw_jobs
