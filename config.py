import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    UPLOAD_FOLDER = os.path.join("app", "static", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # Check if running in Vercel environment
    IS_VERCEL = os.environ.get("VERCEL", "false") == "true" or os.environ.get("NOW_REGION") is not None
    
    if IS_VERCEL:
        default_db = "sqlite:////tmp/app.db"
    else:
        default_db = "sqlite:///" + os.path.join(os.path.abspath(os.path.dirname(__file__)), "instance", "app.db").replace("\\", "/")

    # Auto-adjust postgres protocol for SQLAlchemy compatibility
    database_url = os.environ.get("DATABASE_URL", default_db)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
