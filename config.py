import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    UPLOAD_FOLDER = os.path.join("app", "static", "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(os.path.abspath(os.path.dirname(__file__)), "instance", "app.db").replace("\\", "/")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
