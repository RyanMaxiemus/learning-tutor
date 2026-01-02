from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # Project paths
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOADS_DIR: Path = DATA_DIR / "uploads"
    
    # Database
    DATABASE_URL: str = f"sqlite:///{DATA_DIR}/learning_tutor.db"
    
    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    
    # Vector DB
    CHROMA_PERSIST_DIR: str = str(DATA_DIR / "chroma_db")
    
    # App settings
    SESSION_DURATION_MINUTES: int = 30
    QUESTIONS_PER_SESSION: int = 15
    
    class Config:
        env_file = ".env"

settings = Settings()

# Create necessary directories
settings.DATA_DIR.mkdir(exist_ok=True)
settings.UPLOADS_DIR.mkdir(exist_ok=True)