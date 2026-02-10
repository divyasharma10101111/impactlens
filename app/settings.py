import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./local.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
APP_TIMEZONE = os.getenv("APP_TIMEZONE", "Asia/Kolkata")
