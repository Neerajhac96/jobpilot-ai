# JobPilot AI

An AI-powered autonomous job search, analysis, and application agent.

## Architecture
- **Backend**: FastAPI
- **Database**: SQLite with SQLAlchemy + Alembic
- **Dashboard**: Streamlit
- **LLM**: Groq API
- **Browser**: Playwright

## Features
- Resume Parsing
- Job Discovery via Remotive
- Deep Job Analysis & Ranking
- Tailored Resume Generation
- Application Preparation
- Local Safe Browser Automation Dry Runs
- Daily Job Scheduler

## Installation

1. Create a virtual environment:
   `python -m venv .venv`
2. Activate it:
   `.\.venv\Scripts\Activate.ps1`
3. Install dependencies:
   `pip install -r requirements.txt`
4. Initialize Playwright:
   `playwright install`

## Environment Variables
Create a `.env` file in the root directory:
```
GROQ_API_KEY=your_key
GROQ_MODEL=openai/gpt-oss-20b
JOB_SEARCH_KEYWORDS=Data Analyst
JOB_SEARCH_LOCATIONS=Delhi NCR,Noida,Gurgaon,Remote
JOB_SEARCH_REMOTE=true
JOB_SEARCH_MAX_RESULTS=20
JOB_SEARCH_POSTED_WITHIN_DAYS=7
JOB_SEARCH_INTERVAL_MINUTES=1440
```

## Database Setup
Run Alembic migrations to set up or update the database:
`alembic upgrade head`

## Running Locally

**Terminal 1 (Backend API & Scheduler)**:
```
$env:PYTHONPATH="."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 (Dashboard)**:
```
$env:PYTHONPATH="."
streamlit run app/dashboard/dashboard.py --server.port 8501
```

## Running Tests
Run the automated test suite:
```
$env:PYTHONPATH="."
pytest
```

## Safety Limitations
- The scheduler runs daily to Discover, Analyze, and Rank jobs. **It does NOT automatically submit applications.**
- Submissions require explicit user approval via the Dashboard.
- Browser dry-runs halt before final submission.
