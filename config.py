import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
# Load .env file if it exists
load_dotenv(BASE_DIR / ".env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "eldersos-fallback-secret-key-senior-care-2026")
    
    # SQLite database path inside eldersos directory
    raw_db_url = os.getenv("DATABASE_URL", "").strip()
    if not raw_db_url or raw_db_url == "sqlite:///eldersos.db":
        db_path = BASE_DIR / "eldersos.db"
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path.as_posix()}"
    else:
        SQLALCHEMY_DATABASE_URI = raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # Prevent senior users' sessions from expiring while filling forms
    
    # Alert system settings
    ALERT_MODE = os.getenv("ALERT_MODE", "test").lower().strip()
    ALERT_PROVIDER = os.getenv("ALERT_PROVIDER", "console").lower().strip()
    
    # Credentials
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "").strip()
