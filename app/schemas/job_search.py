from pydantic import BaseModel
from typing import List, Optional

class JobSearchRequest(BaseModel):
    keywords: Optional[str] = None
    locations: Optional[List[str]] = None
    remote: Optional[bool] = False
    max_results: Optional[int] = 20
    posted_within_days: Optional[int] = None
    source: Optional[str] = None
