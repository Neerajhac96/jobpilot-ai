from dataclasses import dataclass

@dataclass
class RawJob:
    title: str
    company: str
    location: str | None
    job_url: str
    source: str
    description: str | None = None
    requirements: str | None = None
    salary: str | None = None
    experience: str | None = None
    employment_type: str | None = None
    posted_date: str | None = None

class JobSource:
    source_name: str = 'base'

    def collect(self, search_params) -> list[RawJob]:
        raise NotImplementedError('Each job source must implement collect()')
