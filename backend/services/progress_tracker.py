from sqlalchemy.orm import Session
from backend.models.session import Session as SessionModel
from backend.models.question import Progress, Interaction
from typing import Dict
from datetime import datetime

class ProgressTracker:
    def __init__(self, db: Session):
        self.db = db
    
    def update_progress(
        self,
        user_id: int,
        subject: str,
        topic: str,
        is_correct: bool
    ):
        """Update user's mastery level for a topic"""
        progress = self.db.query(Progress).filter(
            Progress.user_id == user_id,
            Progress.subject == subject,
            Progress.topic == topic
        ).first()
        
        if not progress:
            progress = Progress(
                user_id=user_id,
                subject=subject,
                topic=topic,
                mastery_level=0.0,
                times_practiced=0
            )
            self.db.add(progress)
        
        # Update mastery using exponential moving average
        # Correct answer: increase mastery, incorrect: decrease
        alpha = 0.2  # Learning rate
        if is_correct:
            progress.mastery_level = progress.mastery_level + alpha * (1.0 - progress.mastery_level)
        else:
            progress.mastery_level = progress.mastery_level * (1 - alpha)
        
        progress.times_practiced += 1
        progress.last_practiced = datetime.utcnow()
        
        self.db.commit()
    
    def get_subject_progress(self, user_id: int, subject: str) -> Dict:
        """Get overall progress for a subject"""
        progress_records = self.db.query(Progress).filter(
            Progress.user_id == user_id,
            Progress.subject == subject
        ).all()
        
        if not progress_records:
            return {
                "subject": subject,
                "overall_mastery": 0.0,
                "topics_started": 0,
                "topics_mastered": 0
            }
        
        avg_mastery = sum(p.mastery_level for p in progress_records) / len(progress_records)
        topics_mastered = sum(1 for p in progress_records if p.mastery_level >= 0.8)
        
        return {
            "subject": subject,
            "overall_mastery": avg_mastery,
            "topics_started": len(progress_records),
            "topics_mastered": topics_mastered,
            "topics": [
                {
                    "topic": p.topic,
                    "mastery": p.mastery_level,
                    "times_practiced": p.times_practiced,
                    "last_practiced": p.last_practiced
                }
                for p in progress_records
            ]
        }
    
    def suggest_next_topic(self, user_id: int, subject: str) -> str:
        """Suggest what to study next based on progress"""
        progress_records = self.db.query(Progress).filter(
            Progress.user_id == user_id,
            Progress.subject == subject
        ).order_by(Progress.mastery_level.asc()).all()
        
        # Find topic that needs most practice
        for progress in progress_records:
            if progress.mastery_level < 0.8:
                return progress.topic
        
        # All topics mastered or no progress yet
        return "New Topic"

progress_tracker = ProgressTracker