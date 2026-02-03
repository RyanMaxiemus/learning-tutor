from backend.database.db import init_db, SessionLocal
from backend.models.user import User
from backend.models.session import Session as SessionModel
from backend.models.question import Interaction, Progress
from backend.models.material import StudyMaterial, Annotation


def setup_database():
    """
    Initialize the database and create a default user.
    Run this once when setting up the project.
    """
    print("🗄️  Initializing database...")

    # Create all tables
    init_db()

    # Create default user if not exists
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.username == "default_user").first()
        if not existing_user:
            default_user = User(username="default_user")
            db.add(default_user)
            db.commit()
            print("✓ Default user created.")
        else:
            print("✓ Default user already exists.")
    except Exception as e:
        print(f"Error during setup: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    setup_database()
