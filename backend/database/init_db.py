from backend.database.db import init_db, SessionLocal
from backend.models.user import User
from backend.models.session import Session
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
    
    # Create default user
    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == "default_user").first()
        
        if not progress_records:
            return {
                "subject": subject,
                "overall_mastery": 0.0,
                "topics_started": 0,
                "topics_mastered": 0,
                "topics": []
            }
        
        # Calculate overall statistics
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
                    "mastery_percentage": p.mastery_level * 100,
                    "times_practiced": p.times_practiced,
                    "last_practiced": p.last_practiced.strftime("%Y-%m-%d %H:%M") if p.last_practiced else None,
                    "is_mastered": p.mastery_level >= 0.8
                }
                for p in sorted(progress_records, key=lambda x: x.mastery_level)
            ]
        }
    except Exception as e:
        print(f"Error retrieving subject progress: {e}")
        return {}
    
    def suggest_next_topic(self, user_id: int, subject: str) -> str:
        """
        Suggest what topic to study next based on mastery levels.
        Prioritizes topics with low mastery.
        
        Args:
            user_id: Which user
            subject: Which subject
        
        Returns:
            Topic name to study next
        """
        # Get all progress, ordered by mastery (lowest first)
        progress_records = self.db.query(Progress).filter(
            Progress.user_id == user_id,
            Progress.subject == subject
        ).order_by(Progress.mastery_level.asc()).all()
        
        # Find first topic that needs practice (< 80% mastery)
        for progress in progress_records:
            if progress.mastery_level < 0.8:
                return progress.topic
        
        # All topics mastered or no progress yet
        return None
    
    def get_weak_areas(self, user_id: int, subject: str, threshold: float = 0.6) -> List[Dict]:
        """
        Identify topics that need more practice.
        
        Args:
            user_id: Which user
            subject: Which subject
            threshold: Mastery level below which is considered weak
        
        Returns:
            List of weak topics with details
        """
        weak_topics = self.db.query(Progress).filter(
            Progress.user_id == user_id,
            Progress.subject == subject,
            Progress.mastery_level < threshold
        ).order_by(Progress.mastery_level.asc()).all()
        
        return [
            {
                "topic": p.topic,
                "mastery": p.mastery_level,
                "times_practiced": p.times_practiced,
                "needs_practice": True
            }
            for p in weak_topics
        ]
    
    def get_session_stats(self, session_id: int) -> Dict:
        """
        Get detailed statistics for a completed session.
        
        Args:
            session_id: Which session
        
        Returns:
            Dictionary with session statistics
        """
        session = self.db.query(SessionModel).filter(SessionModel.id == session_id).first()
        
        if not session:
            return {}
        
        interactions = self.db.query(Interaction).filter(
            Interaction.session_id == session_id
        ).all()
        
        # Calculate statistics
        total_time = sum(i.response_time_seconds or 0 for i in interactions)
        avg_time = total_time / len(interactions) if interactions else 0
        
        return {
            "session_id": session_id,
            "subject": session.subject,
            "topic": session.topic,
            "difficulty": session.difficulty_level,
            "questions_answered": session.questions_answered,
            "questions_correct": session.questions_correct,
            "accuracy": session.accuracy,
            "total_time_seconds": total_time,
            "average_time_per_question": avg_time,
            "restart_count": session.restart_count
        }

# Note: Don't create a singleton here since we need db session