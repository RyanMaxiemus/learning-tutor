from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    """
    Central configuration for the entire application.
    Think of this as the app's control panel.
    """
    
    # Project paths - where things are stored
    BASE_DIR: Path = Path(__file__).parent.parent  # Root project folder
    DATA_DIR: Path = BASE_DIR / "data"              # Where data is saved
    UPLOADS_DIR: Path = DATA_DIR / "uploads"        # Where PDFs go
    
    # Database - where your learning progress is stored
    DATABASE_URL: str = f"sqlite:///{DATA_DIR}/learning_tutor.db"
    
    # Ollama settings - connecting to the AI
    OLLAMA_BASE_URL: str = "http://localhost:11434"  # Ollama runs here
    OLLAMA_MODEL: str = "llama3.2"                   # Which AI model to use
    
    # Vector database - for smart document search
    CHROMA_PERSIST_DIR: str = str(DATA_DIR / "chroma_db")
    
    # App behavior settings
    SESSION_DURATION_MINUTES: int = 30   # How long study sessions last
    QUESTIONS_PER_SESSION: int = 15       # Questions per session
    
    class Config:
        env_file = ".env"  # Can override settings with .env file

# Create a single instance to use throughout the app
settings = Settings()

# Create folders if they don't exist
settings.DATA_DIR.mkdir(exist_ok=True)
settings.UPLOADS_DIR.mkdir(exist_ok=True)