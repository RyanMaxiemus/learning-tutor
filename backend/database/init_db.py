from backend.database.db import init_db, SessionLocal
from backend.models.user import User
from backend.models.session import Session
from backend.models.question import Interaction, Progress
from backend.models.material import StudyMaterial, Annotation

def setup_database():
    """Initialize database and create default user"""
    init_db()
    
    # Create default user
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.username == "default_user").first()
        if not existing_user:
            user = User(username="default_user")
            db.add(user)
            db.commit()
            print("✓ Default user created")
        else:
            print("✓ Default user already exists")
    finally:
        db.close()

if __name__ == "__main__":
    setup_database()