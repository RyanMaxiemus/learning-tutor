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

    # NOTE: We intentionally do NOT create a passwordless default user.
    # Users should register via the Streamlit UI so their password is properly hashed.


if __name__ == "__main__":
    setup_database()
