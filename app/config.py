import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b')
    JOB_SEARCH_KEYWORDS = os.getenv('JOB_SEARCH_KEYWORDS', 'Data Analyst')
    JOB_SEARCH_LOCATIONS = os.getenv('JOB_SEARCH_LOCATIONS', 'Delhi NCR,Noida,Gurgaon,Remote')
    JOB_SEARCH_REMOTE = os.getenv('JOB_SEARCH_REMOTE', 'true').lower() == 'true'
    JOB_SEARCH_MAX_RESULTS = int(os.getenv('JOB_SEARCH_MAX_RESULTS', '20'))
    JOB_SEARCH_POSTED_WITHIN_DAYS = int(os.getenv('JOB_SEARCH_POSTED_WITHIN_DAYS', '7'))
    JOB_SEARCH_INTERVAL_MINUTES = int(os.getenv('JOB_SEARCH_INTERVAL_MINUTES', '1440'))
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', '8000'))
    DASHBOARD_PORT = int(os.getenv('DASHBOARD_PORT', '8501'))
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///jobpilot.db')

settings = Settings()
