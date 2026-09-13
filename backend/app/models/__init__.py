"""Model registry: importing this package registers every table on Base.metadata."""
from app.db.base import Base
from app.models.user import User, UserRole
from app.models.user_relations import User as _UserRelationsWiring  # noqa: F401
from app.models.profile import StudentProfile, TeacherProfile
from app.models.content import Company, TeacherStudent, Topic
from app.models.question import Question, QuestionOption
from app.models.assessment import (
    Answer,
    Assessment,
    AssessmentQuestion,
    Attempt,
)
from app.models.performance import PerformanceSnapshot, TopicPerformance
from app.models.roadmap import Recommendation, Roadmap, RoadmapItem
from app.models.mission import Mission, StudentMission
from app.models.gamification import Badge, StudentBadge, XPTransaction
from app.models.leaderboard import Leaderboard, LeaderboardEntry
from app.models.coding import CodingProblem, CodeSubmission, TestCase
from app.models.activity import ActivityEvent

__all__ = [
    "Base",
    "User",
    "UserRole",
    "StudentProfile",
    "TeacherProfile",
    "TeacherStudent",
    "Topic",
    "Company",
    "Question",
    "QuestionOption",
    "Assessment",
    "AssessmentQuestion",
    "Attempt",
    "Answer",
    "TopicPerformance",
    "PerformanceSnapshot",
    "Roadmap",
    "RoadmapItem",
    "Recommendation",
    "Mission",
    "StudentMission",
    "Badge",
    "StudentBadge",
    "XPTransaction",
    "Leaderboard",
    "LeaderboardEntry",
    "CodingProblem",
    "TestCase",
    "CodeSubmission",
    "ActivityEvent",
]
