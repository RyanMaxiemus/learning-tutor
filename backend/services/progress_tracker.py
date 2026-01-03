from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from backend.models.session import Session as SessionModel
from backend.models.question import Progress, Interaction
from backend.models.user import User
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger

class ProgressTracker:
    """
    Tracks user learning progress and mastery levels.
    
    Uses an exponential moving average algorithm to calculate mastery:
    - Recent performance is weighted more heavily than old performance
    - Correct answers push mastery toward 100%
    - Incorrect answers pull mastery down
    - Prevents both "instant mastery" and "permanent failure"
    
    Mastery Levels:
    - 0.0 - 0.4: Novice (needs lots of practice)
    - 0.4 - 0.6: Learning (making progress)
    - 0.6 - 0.8: Proficient (solid understanding)
    - 0.8 - 1.0: Mastered (excellent grasp)
    """
    
    def __init__(self, db: Session):
        """
        Initialize tracker with database session.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.alpha = 0.2  # Learning rate - how quickly mastery changes
        # Lower alpha = slower changes, more stable
        # Higher alpha = faster changes, more volatile
    
    def update_progress(
        self,
        user_id: int,
        subject: str,
        topic: str,
        is_correct: bool
    ) -> float:
        """
        Update mastery level for a topic based on performance.
        
        Algorithm: Exponential Moving Average (EMA)
        
        If correct:
            new_mastery = old_mastery + α × (1.0 - old_mastery)
            (Push toward perfect mastery)
        
        If incorrect:
            new_mastery = old_mastery × (1 - α)
            (Pull down but not to zero)
        
        Args:
            user_id: Which user
            subject: Which subject (e.g., "Python")
            topic: Which topic (e.g., "Lists")
            is_correct: Was the answer correct?
        
        Returns:
            Updated mastery level (0.0 to 1.0)
        """
        try:
            # Find existing progress record
            progress = self.db.query(Progress).filter(
                Progress.user_id == user_id,
                Progress.subject == subject,
                Progress.topic == topic
            ).first()
            
            # Create new record if doesn't exist
            if not progress:
                progress = Progress(
                    user_id=user_id,
                    subject=subject,
                    topic=topic,
                    mastery_level=0.0,
                    times_practiced=0
                )
                self.db.add(progress)
                logger.info(f"Created new progress record for {subject}/{topic}")
            
            # Store old mastery for logging
            old_mastery = progress.mastery_level
            
            # Update mastery using exponential moving average
            if is_correct:
                # Move toward 1.0 (perfect)
                progress.mastery_level = progress.mastery_level + self.alpha * (1.0 - progress.mastery_level)
            else:
                # Decrease mastery
                progress.mastery_level = progress.mastery_level * (1 - self.alpha)
            
            # Ensure mastery stays in bounds [0, 1]
            progress.mastery_level = max(0.0, min(1.0, progress.mastery_level))
            
            # Update practice count and timestamp
            progress.times_practiced += 1
            progress.last_practiced = datetime.utcnow()
            
            # Commit changes
            self.db.commit()
            
            # Log the update
            change = progress.mastery_level - old_mastery
            logger.info(
                f"Updated {subject}/{topic}: "
                f"{old_mastery:.2%} → {progress.mastery_level:.2%} "
                f"({'✓' if is_correct else '✗'}, change: {change:+.2%})"
            )
            
            return progress.mastery_level
        
        except Exception as e:
            logger.error(f"Error updating progress: {e}")
            self.db.rollback()
            return 0.0
    
    def get_subject_progress(self, user_id: int, subject: str) -> Dict:
        """
        Get comprehensive progress statistics for a subject.
        
        Args:
            user_id: Which user
            subject: Which subject
        
        Returns:
            Dictionary with:
            - subject: Subject name
            - overall_mastery: Average mastery across all topics
            - topics_started: How many topics have been practiced
            - topics_mastered: How many topics are ≥80% mastered
            - topics: List of all topic details
        """
        try:
            # Get all progress records for this subject
            progress_records = self.db.query(Progress).filter(
                Progress.user_id == user_id,
                Progress.subject == subject
            ).all()
            
            if not progress_records:
                logger.info(f"No progress found for {subject}")
                return {
                    "subject": subject,
                    "overall_mastery": 0.0,
                    "topics_started": 0,
                    "topics_mastered": 0,
                    "topics": []
                }
            
            # Calculate overall statistics
            total_mastery = sum(p.mastery_level for p in progress_records)
            avg_mastery = total_mastery / len(progress_records)
            topics_mastered = sum(1 for p in progress_records if p.mastery_level >= 0.8)
            
            # Build topic details list
            topics_list = []
            for p in sorted(progress_records, key=lambda x: x.mastery_level):
                # Determine mastery category
                if p.mastery_level >= 0.8:
                    category = "mastered"
                elif p.mastery_level >= 0.6:
                    category = "proficient"
                elif p.mastery_level >= 0.4:
                    category = "learning"
                else:
                    category = "novice"
                
                topics_list.append({
                    "topic": p.topic,
                    "mastery": p.mastery_level,
                    "mastery_percentage": p.mastery_level * 100,
                    "category": category,
                    "times_practiced": p.times_practiced,
                    "last_practiced": p.last_practiced.strftime("%Y-%m-%d %H:%M") if p.last_practiced else None,
                    "is_mastered": p.mastery_level >= 0.8
                })
            
            logger.info(
                f"Retrieved progress for {subject}: "
                f"{len(progress_records)} topics, "
                f"{avg_mastery:.1%} average mastery"
            )
            
            return {
                "subject": subject,
                "overall_mastery": avg_mastery,
                "topics_started": len(progress_records),
                "topics_mastered": topics_mastered,
                "topics": topics_list
            }
        
        except Exception as e:
            logger.error(f"Error getting subject progress: {e}")
            return {
                "subject": subject,
                "overall_mastery": 0.0,
                "topics_started": 0,
                "topics_mastered": 0,
                "topics": []
            }
    
    def suggest_next_topic(self, user_id: int, subject: str) -> Optional[str]:
        """
        Suggest what topic to study next based on mastery levels.
        
        Strategy:
        1. Prioritize topics with lowest mastery (< 80%)
        2. If all mastered, return None (suggest exploring new topics)
        
        Args:
            user_id: Which user
            subject: Which subject
        
        Returns:
            Topic name to study next, or None if all mastered
        """
        try:
            # Get all progress, ordered by mastery (lowest first)
            progress_records = self.db.query(Progress).filter(
                Progress.user_id == user_id,
                Progress.subject == subject
            ).order_by(Progress.mastery_level.asc()).all()
            
            # Find first topic that needs practice (< 80% mastery)
            for progress in progress_records:
                if progress.mastery_level < 0.8:
                    logger.info(f"Suggested next topic: {progress.topic} ({progress.mastery_level:.1%} mastery)")
                    return progress.topic
            
            # All topics mastered
            logger.info(f"All topics in {subject} are mastered!")
            return None
        
        except Exception as e:
            logger.error(f"Error suggesting next topic: {e}")
            return None
    
    def get_weak_areas(
        self,
        user_id: int,
        subject: str,
        threshold: float = 0.6
    ) -> List[Dict]:
        """
        Identify topics that need more practice.
        
        Args:
            user_id: Which user
            subject: Which subject
            threshold: Mastery level below which is considered "weak"
        
        Returns:
            List of weak topics with details, ordered by mastery (lowest first)
        """
        try:
            weak_topics = self.db.query(Progress).filter(
                Progress.user_id == user_id,
                Progress.subject == subject,
                Progress.mastery_level < threshold
            ).order_by(Progress.mastery_level.asc()).all()
            
            result = [
                {
                    "topic": p.topic,
                    "mastery": p.mastery_level,
                    "mastery_percentage": p.mastery_level * 100,
                    "times_practiced": p.times_practiced,
                    "needs_practice": True,
                    "gap_to_proficiency": (0.6 - p.mastery_level) * 100  # How far from 60%
                }
                for p in weak_topics
            ]
            
            logger.info(f"Found {len(result)} weak areas in {subject}")
            return result
        
        except Exception as e:
            logger.error(f"Error getting weak areas: {e}")
            return []
    
    def get_session_stats(self, session_id: int) -> Dict:
        """
        Get detailed statistics for a completed session.
        
        Args:
            session_id: Which session
        
        Returns:
            Dictionary with comprehensive session statistics
        """
        try:
            session = self.db.query(SessionModel).filter(
                SessionModel.id == session_id
            ).first()
            
            if not session:
                logger.warning(f"Session {session_id} not found")
                return {}
            
            # Get all interactions for this session
            interactions = self.db.query(Interaction).filter(
                Interaction.session_id == session_id
            ).all()
            
            if not interactions:
                logger.warning(f"No interactions found for session {session_id}")
                return {
                    "session_id": session_id,
                    "subject": session.subject,
                    "topic": session.topic,
                    "questions_answered": 0
                }
            
            # Calculate statistics
            total_time = sum(i.response_time_seconds or 0 for i in interactions)
            avg_time = total_time / len(interactions) if interactions else 0
            
            # Calculate difficulty progression
            first_half_accuracy = sum(
                1 for i in interactions[:len(interactions)//2] if i.is_correct
            ) / max(len(interactions)//2, 1) * 100
            
            second_half_accuracy = sum(
                1 for i in interactions[len(interactions)//2:] if i.is_correct
            ) / max(len(interactions) - len(interactions)//2, 1) * 100
            
            improvement = second_half_accuracy - first_half_accuracy
            
            return {
                "session_id": session_id,
                "subject": session.subject,
                "topic": session.topic,
                "difficulty": session.difficulty_level,
                "questions_answered": session.questions_answered,
                "questions_correct": session.questions_correct,
                "accuracy": session.accuracy,
                "total_time_seconds": total_time,
                "average_time_per_question": round(avg_time, 1),
                "fastest_answer": min((i.response_time_seconds for i in interactions if i.response_time_seconds), default=0),
                "slowest_answer": max((i.response_time_seconds for i in interactions if i.response_time_seconds), default=0),
                "first_half_accuracy": round(first_half_accuracy, 1),
                "second_half_accuracy": round(second_half_accuracy, 1),
                "improvement": round(improvement, 1),
                "restart_count": session.restart_count,
                "start_time": session.start_time.isoformat(),
                "end_time": session.end_time.isoformat() if session.end_time else None
            }
        
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            return {}
    
    def get_study_streak(self, user_id: int) -> Dict:
        """
        Calculate the user's study streak (consecutive days studied).
        
        Args:
            user_id: Which user
        
        Returns:
            Dictionary with current streak and longest streak
        """
        try:
            # Get all sessions ordered by date
            sessions = self.db.query(SessionModel).filter(
                SessionModel.user_id == user_id,
                SessionModel.status == "completed"
            ).order_by(SessionModel.start_time.desc()).all()
            
            if not sessions:
                return {
                    "current_streak": 0,
                    "longest_streak": 0,
                    "last_study_date": None
                }
            
            # Calculate current streak
            current_streak = 0
            current_date = datetime.utcnow().date()
            
            # Get unique study dates
            study_dates = sorted(set(s.start_time.date() for s in sessions), reverse=True)
            
            for date in study_dates:
                if date == current_date or date == current_date - timedelta(days=current_streak):
                    current_streak += 1
                    current_date = date
                else:
                    break
            
            # Calculate longest streak
            longest_streak = 1
            temp_streak = 1
            
            for i in range(1, len(study_dates)):
                if study_dates[i-1] - study_dates[i] == timedelta(days=1):
                    temp_streak += 1
                    longest_streak = max(longest_streak, temp_streak)
                else:
                    temp_streak = 1
            
            return {
                "current_streak": current_streak,
                "longest_streak": longest_streak,
                "last_study_date": study_dates[0].isoformat() if study_dates else None,
                "total_study_days": len(study_dates)
            }
        
        except Exception as e:
            logger.error(f"Error calculating study streak: {e}")
            return {
                "current_streak": 0,
                "longest_streak": 0,
                "last_study_date": None
            }
    
    def get_all_subjects(self, user_id: int) -> List[str]:
        """
        Get list of all subjects the user has studied.
        
        Args:
            user_id: Which user
        
        Returns:
            List of unique subject names
        """
        try:
            subjects = self.db.query(Progress.subject).filter(
                Progress.user_id == user_id
            ).distinct().all()
            
            return [s[0] for s in subjects]
        
        except Exception as e:
            logger.error(f"Error getting subjects: {e}")
            return []
    
    def get_global_stats(self, user_id: int) -> Dict:
        """
        Get overall learning statistics across all subjects.
        
        Args:
            user_id: Which user
        
        Returns:
            Dictionary with global statistics
        """
        try:
            # Get all progress records
            all_progress = self.db.query(Progress).filter(
                Progress.user_id == user_id
            ).all()
            
            # Get all sessions
            all_sessions = self.db.query(SessionModel).filter(
                SessionModel.user_id == user_id
            ).all()
            
            # Get all interactions
            total_questions = self.db.query(func.count(Interaction.id)).join(
                SessionModel
            ).filter(
                SessionModel.user_id == user_id
            ).scalar()
            
            total_correct = self.db.query(func.count(Interaction.id)).join(
                SessionModel
            ).filter(
                SessionModel.user_id == user_id,
                Interaction.is_correct == True
            ).scalar()
            
            # Calculate statistics
            overall_accuracy = (total_correct / total_questions * 100) if total_questions > 0 else 0
            
            avg_mastery = (
                sum(p.mastery_level for p in all_progress) / len(all_progress)
                if all_progress else 0
            )
            
            subjects_count = len(set(p.subject for p in all_progress))
            topics_count = len(all_progress)
            mastered_topics = sum(1 for p in all_progress if p.mastery_level >= 0.8)
            
            # Get streak info
            streak_info = self.get_study_streak(user_id)
            
            return {
                "total_sessions": len(all_sessions),
                "total_questions_answered": total_questions or 0,
                "total_correct_answers": total_correct or 0,
                "overall_accuracy": round(overall_accuracy, 1),
                "subjects_studied": subjects_count,
                "topics_practiced": topics_count,
                "topics_mastered": mastered_topics,
                "average_mastery": round(avg_mastery * 100, 1),
                "current_streak": streak_info["current_streak"],
                "longest_streak": streak_info["longest_streak"],
                "total_study_days": streak_info.get("total_study_days", 0)
            }
        
        except Exception as e:
            logger.error(f"Error getting global stats: {e}")
            return {}

# Note: Don't create a singleton here since we need db session