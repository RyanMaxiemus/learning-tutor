from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database.db import Base

class User(Base):
    """
    Represents a user in the system.
    For now, we just have one default user, but this allows
    for multiple users in the future.
    """
    __tablename__ = "users"
    
    # Columns (like spreadsheet columns)
    id = Column(Integer, primary_key=True)  # Unique ID for each user
    username = Column(String, unique=True, nullable=False)  # Username (must be unique)
    created_at = Column(DateTime, default=datetime.utcnow)  # When account was created
    
    # Relationships - connections to other tables
    sessions = relationship("Session", back_populates="user")  # User's study sessions
    materials = relationship("StudyMaterial", back_populates="user")  # User's uploaded files
    
    def __repr__(self):
        """How this object appears when printed"""
        return f"<User(id={self.id}, username='{self.username}')>"