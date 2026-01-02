from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database.db import Base

class Session(Base):
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject = Column(String, nullable=False)
    topic = Column(String)
    difficulty_level = Column(String, default="beginner")  # beginner/intermediate/advanced
    
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    
    questions_answered = Column(Integer, default=0)
    questions_correct = Column(Integer, default=0)
    
    restart_count = Column(Integer, default=0)
    difficulty_changes = Column(JSON)  # Track difficulty switches
    
    status = Column(String, default="active")  # active/completed/restarted
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    interactions = relationship("Interaction", back_populates="session")