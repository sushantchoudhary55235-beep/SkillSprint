"""Teacher Dashboard service (docs/Phases.md §16 — Phase 12).

Teachers monitor ONLY students associated with them via ``teacher_students``.
Association happens by the student's unique public Student ID (SS…).
All metrics come from the Phase 7 performance engine — teachers see the same
deterministic analytics students see, never self-reported data.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.content import TeacherStudent
from app.models.profile import StudentProfile, TeacherProfile
from app.models.user import User
from app.schemas.performance import classify_accuracy


class TeacherService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ============================================================ ASSOCIATION

    def add_student(self, teacher: TeacherProfile, student_code: str) -> TeacherStudent:
        """Associate a student by their public Student ID (status=ACTIVE)."""
        code = student_code.strip().upper()
        profile = self.db.scalar(
            select(StudentProfile).where(StudentProfile.student_id == code)
        )
        if profile is None:
            raise NotFoundError(f"No student found with ID {code}")
        if profile.user_id == teacher.user_id:
            raise ValidationError("A teacher cannot add themselves as a student")

        existing = self.db.scalar(
            select(TeacherStudent).where(
                TeacherStudent.teacher_id == teacher.id,
                TeacherStudent.student_id == profile.id,
            )
        )
        if existing is not None:
            if existing.status == "REMOVED":
                existing.status = "ACTIVE"
                self.db.commit()
                self.db.refresh(existing)
                return existing
            raise ConflictError("Student is already associated with you")

        link = TeacherStudent(teacher_id=teacher.id, student_id=profile.id, status="ACTIVE")
        self.db.add(link)
        self.db.commit()
        self.db.refresh(link)
        return link

    def remove_student(self, teacher: TeacherProfile, student_profile_id: int) -> None:
        link = self.db.scalar(
            select(TeacherStudent).where(
                TeacherStudent.teacher_id == teacher.id,
                TeacherStudent.student_id == student_profile_id,
            )
        )
        if link is None:
            raise NotFoundError("Student is not associated with you")
        link.status = "REMOVED"
        self.db.commit()

    def list_students(self, teacher: TeacherProfile) -> list[dict]:
        """Overview of all associated students with headline metrics."""
        rows = self.db.execute(
            select(TeacherStudent, StudentProfile, User)
            .join(StudentProfile, TeacherStudent.student_id == StudentProfile.id)
            .join(User, StudentProfile.user_id == User.id)
            .where(TeacherStudent.teacher_id == teacher.id)
            .where(TeacherStudent.status == "ACTIVE")
            .order_by(User.name)
        ).all()
        return [self._student_row(link, profile, user) for link, profile, user in rows]

    def _student_row(self, link: TeacherStudent, profile: StudentProfile, user: User) -> dict:
        from app.services.performance import PerformanceService

        overall = PerformanceService(self.db).get_overall(profile)
        return {
            "association_id": link.id,
            "student_profile_id": profile.id,
            "student_id": profile.student_id,
            "name": user.name,
            "email": user.email,
            "xp": profile.xp,
            "level": profile.level,
            "current_streak": profile.current_streak,
            "overall_accuracy": overall.overall_accuracy,
            "classification": overall.classification,
            "assessment_avg_score": overall.assessment_avg_score,
            "questions_attempted": overall.total_questions_attempted,
        }

    # ============================================================ ACCESS CONTROL

    def get_associated_student(self, teacher: TeacherProfile, student_profile_id: int) -> dict:
        """Full performance view for an associated student; 403 otherwise."""
        link = self.db.scalar(
            select(TeacherStudent).where(
                TeacherStudent.teacher_id == teacher.id,
                TeacherStudent.student_id == student_profile_id,
                TeacherStudent.status == "ACTIVE",
            )
        )
        if link is None:
            raise ForbiddenError("Student is not associated with you")

        profile = self.db.get(StudentProfile, student_profile_id)
        user = self.db.get(User, profile.user_id)
        return self.student_detail(profile, user)

    def student_detail(self, profile: StudentProfile, user: User) -> dict:
        from app.services.performance import PerformanceService
        from app.services.coding import CodingService

        perf = PerformanceService(self.db)
        overall = perf.get_overall(profile)
        topics = perf.get_topics(profile)
        coding = CodingService(self.db).performance(profile)
        weak = [t for t in topics if t.classification == "weak" and t.total_attempts >= 3]
        strong = [t for t in topics if t.classification == "strong" and t.total_attempts >= 3]

        return {
            "student_profile_id": profile.id,
            "student_id": profile.student_id,
            "name": user.name,
            "email": user.email,
            "xp": profile.xp,
            "level": profile.level,
            "current_streak": profile.current_streak,
            "overall": overall.model_dump(),
            "topics": [t.model_dump() for t in topics],
            "weak_topics": [
                {"topic_id": t.topic_id, "topic_name": t.topic_name, "accuracy": t.accuracy}
                for t in weak
            ],
            "strong_topics": [
                {"topic_id": t.topic_id, "topic_name": t.topic_name, "accuracy": t.accuracy}
                for t in strong
            ],
            "coding": coding,
        }

    # ============================================================ DASHBOARD

    def dashboard(self, teacher: TeacherProfile) -> dict:
        students = self.list_students(teacher)
        n = len(students)
        accuracies = [s["overall_accuracy"] for s in students if s["overall_accuracy"] is not None]
        scores = [s["assessment_avg_score"] for s in students if s["assessment_avg_score"] is not None]
        avg_accuracy = round(sum(accuracies) / len(accuracies), 2) if accuracies else None
        avg_score = round(sum(scores) / len(scores), 2) if scores else None

        # Aggregate weak topics across the class (deterministic counts).
        weak_topics: dict[str, dict] = {}
        for sid in (s["student_profile_id"] for s in students):
            detail = self.db.get(StudentProfile, sid)
            user = self.db.get(User, detail.user_id)
            topics = self.student_detail(detail, user)["weak_topics"]
            for t in topics:
                bucket = weak_topics.setdefault(t["topic_name"], {"topic_id": t["topic_id"], "count": 0})
                bucket["count"] += 1
        weak_ranked = sorted(
            ({"topic_name": k, **v} for k, v in weak_topics.items()),
            key=lambda x: (-x["count"], x["topic_name"]),
        )

        return {
            "total_students": n,
            "average_accuracy": avg_accuracy,
            "average_assessment_score": avg_score,
            "students": students,
            "weak_topics_class_wide": weak_ranked[:10],
            "students_needing_attention": self.students_needing_attention(teacher),
        }

    def students_needing_attention(self, teacher: TeacherProfile) -> list[dict]:
        """Students flagged by documented, non-sensitive rules (Feature Group 16).

        Rules (any one flags a student):
        - LOW_ACCURACY:   recent overall accuracy < 50% (≥5 answered questions)
        - DECLINING:      any tracked topic with trend == DECLINING
        - INACTIVE:       no learning activity in the last 7 days

        Only academic/activity signals are used — never personal characteristics.
        """
        from datetime import datetime, timedelta, timezone

        from app.models.activity import ActivityEvent

        now = datetime.now(timezone.utc)
        week_ago = now - timedelta(days=7)
        flags: list[dict] = []
        for row in self.list_students(teacher):
            profile = self.db.get(StudentProfile, row["student_profile_id"])
            reasons: list[str] = []

            accuracy = row["overall_accuracy"]
            if accuracy is not None and accuracy < 50 and row["questions_attempted"] >= 5:
                reasons.append("LOW_ACCURACY")

            topics = self.student_detail(profile, self.db.get(User, profile.user_id))["topics"]
            if any(t.get("trend") == "DECLINING" for t in topics):
                reasons.append("DECLINING")

            last_activity = self.db.scalar(
                select(ActivityEvent.created_at)
                .where(ActivityEvent.student_id == profile.id)
                .order_by(ActivityEvent.created_at.desc())
                .limit(1)
            )
            if last_activity is None:
                reasons.append("INACTIVE")
            else:
                aware = last_activity.replace(tzinfo=timezone.utc) if last_activity.tzinfo is None else last_activity
                if aware < week_ago:
                    reasons.append("INACTIVE")

            if reasons:
                flags.append({
                    "student_profile_id": profile.id,
                    "student_id": profile.student_id,
                    "name": row["name"],
                    "reasons": reasons,
                    "overall_accuracy": accuracy,
                })
        return flags
