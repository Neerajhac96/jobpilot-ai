from app.jobs.collector import JobSource, RawJob


class TestJobSource(JobSource):
    source_name = 'test_source'

    def collect(self, search_params=None) -> list[RawJob]:

        return [
            RawJob(
                title="Data Analyst",
                company="Test Analytics",
                location="Noida, Uttar Pradesh",
                job_url="https://example.com/job/data-analyst-001",
                source="test_source",
                description=(
                    "We are looking for a Data Analyst "
                    "to analyze business data."
                ),
                requirements=(
                    "Python, SQL, Excel, Power BI, "
                    "Pandas, data visualization"
                ),
                salary="₹4-7 LPA",
                experience="0-2 years",
                employment_type="Full-time",
                posted_date="2026-08-18"
            ),

            RawJob(
                title="Junior Python Developer",
                company="Test Software",
                location="Gurgaon, Haryana",
                job_url="https://example.com/job/python-002",
                source="test_source",
                description=(
                    "Looking for a junior Python developer "
                    "to build backend applications."
                ),
                requirements=(
                    "Python, FastAPI, SQL, Git, REST API"
                ),
                salary="₹4-8 LPA",
                experience="0-2 years",
                employment_type="Full-time",
                posted_date="2026-08-18"
            )
        ]
