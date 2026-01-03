from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config.settings import settings

# Create the database engine
# Think of this as opening a connection to your database file
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}  # Needed for SQLite threading
)

# Create a session factory
# Sessions are how we talk to the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all database models
# Every table will inherit from this
Base = declarative_base()

def get_db():
    """
    Creates a database session for each request.
    Automatically closes it when done (even if errors occur).
    """
    db = SessionLocal()
    try:
        yield db  # Give the session to whoever needs it
    finally:
        db.close()  # Always close when done

def init_db():
    """
    Creates all database tables.
    Run this once to set up your database.
    """
    # Import all models so SQLAlchemy knows about them
    from backend.models import user, session, question, material
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("✓ Database initialized successfully!")