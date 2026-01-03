from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database.db import Base

class Session(Base):
    """
    Represents a single study session.
    Tracks what you studied, how long, and your performance.
    """
    __tablename__ = "sessions"
    
    # Basic info
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))  # Which user
    subject = Column(String, nullable=False)  # e.g., "Python Programming"
    topic = Column(String)  # e.g., "Control Flow"
    difficulty_level = Column(String, default="beginner")  # beginner/intermediate/advanced
    
    # Timing
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)  # When session ended (null if still active)
    
    # Performance tracking
    questions_answered = Column(Integer, default=0)  # Total questions attempted
    questions_correct = Column(Integer, default=0)   # How many were correct
    
    # Restart functionality
    restart_count = Column(Integer, default=0)  # How many times restarted
    difficulty_changes = Column(JSON)  # List of difficulty changes
    # Example: [{"from": "intermediate", "to": "beginner", "at_question": 5, "timestamp": "..."}]
    
    status = Column(String, default="active")  # active/completed/restarted
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    interactions = relationship("Interaction", back_populates="session")  # Questions in this session
    
    def __repr__(self):
        return f"<Session(id={self.id}, subject='{self.subject}', difficulty='{self.difficulty_level}')>"
    
    @property
    def accuracy(self):
        """Calculate accuracy percentage"""
        if self.questions_answered == 0:
            return 0.0
        return (self.questions_correct / self.questions_answered) * 100