from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from backend.database.db import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subject = Column(String(200), nullable=False)
    topic = Column(String(200), nullable=False)
    difficulty_level = Column(String(20), nullable=False, default="beginner")
    status = Column(String(20), nullable=False, default="active")  # active | completed
    questions_answered = Column(Integer, nullable=False, default=0)
    questions_correct = Column(Integer, nullable=False, default=0)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    restart_count = Column(Integer, nullable=False, default=0)
    difficulty_changes = Column(String(1000), nullable=True)  # JSON list of changes

    @property
    def accuracy(self) -> float:
        """Percentage of correct answers (0-100)."""
        if self.questions_answered == 0:
            return 0.0
        return (self.questions_correct / self.questions_answered) * 100.0
