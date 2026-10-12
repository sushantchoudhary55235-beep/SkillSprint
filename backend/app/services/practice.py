"""Practice service: business logic for the student learning system.

Phase 5 completion criteria (docs/Phases.md §9):
- Student can select topics.
- Student can practice questions.
- Answers are recorded.
- Score is calculated.
- Results are displayed.
- Attempts are stored.
- Performance data is generated.
"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.practice import PracticeAnswer, PracticeSession
from app.models.profile import StudentProfile
from app.models.question import Question, QuestionOption
from app.repositories.practice import PracticeRepository
from app.schemas.practice import (
    DashboardData,
    OverallProgressData,
    PracticeAnswerData,
    PracticeAnswerRequest,
    PracticeCompleteData,
    PracticeHistoryData,
    PracticeStartData,
    PracticeStartRequest,
    PracticeSessionSummary,
    QuestionForPractice,
    QuestionOptionOut,
    TopicProgressItem,
)
from app.services.content import ContentService

# XP rules (docs/Phases.md §14.1) — single source of truth lives in the
# gamification service; these aliases preserve the Phase 5 test expectations.
from app.services.gamification import (
    XP_COMPLETE_SESSION_BONUS as _XP_COMPLETE_SESSION_BONUS,
    XP_CORRECT_ANSWER as _XP_CORRECT_ANSWER,
    XP_DAILY_QUIZ_BONUS as _XP_DAILY_QUIZ_BONUS,
)


class PracticeService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PracticeRepository(db)

    # ============================================================ START

    def start_session(
        self, req: PracticeStartRequest, student: StudentProfile
    ) -> PracticeStartData:
        """Create a new practice session and return randomized questions."""
        # Must have at least one filter
        if req.topic_id is None and req.company_id is None:
            raise ValidationError("At least one of topic_id or company_id must be provided")

        mode = "TOPIC" if req.topic_id is not None else "COMPANY"
        if req.company_id and req.topic_id:
            mode = "TOPIC"

        questions = self.repo.get_random_questions(
            topic_id=req.topic_id,
            company_id=req.company_id,
            difficulty=req.difficulty,
            count=req.question_count,
        )
        if not questions:
            raise NotFoundError("No questions available for the selected filters")

        session = PracticeSession(
            student_id=student.id,
            mode=mode,
            topic_id=req.topic_id,
            company_id=req.company_id,
            difficulty=req.difficulty,
            question_count=len(questions),
            status="IN_PROGRESS",
        )
        self.repo.create_session(session)
        self.repo.commit()

        q_out = []
        for q in questions:
            q_out.append(
                QuestionForPractice(
                    id=q.id,
                    question_text=q.question_text,
                    question_type=q.question_type,
                    difficulty=q.difficulty,
                    options=[QuestionOptionOut.model_validate(o) for o in q.options],
                )
            )

        return PracticeStartData(
            session_id=session.id,
            mode=mode,
            topic_id=req.topic_id,
            company_id=req.company_id,
            difficulty=req.difficulty,
            question_count=len(questions),
            questions=q_out,
        )

    # ============================================================ ANSWER

    def submit_answer(
        self,
        session_id: int,
        req: PracticeAnswerRequest,
        student: StudentProfile,
    ) -> PracticeAnswerData:
        """Evaluate a single answer within an active session."""
        session = self.repo.get_session(session_id)
        if session is None:
            raise NotFoundError(f"Session {session_id} not found")
        if session.student_id != student.id:
            raise ValidationError("Session does not belong to this student")
        if session.status != "IN_PROGRESS":
            raise ConflictError("Session is no longer in progress")

        # Verify question exists and is valid MCQ
        question = self.db.get(Question, req.question_id)
        if question is None:
            raise NotFoundError(f"Question {req.question_id} not found")

        # Server-side correctness evaluation
        is_correct = False
        correct_option_id = None
        if req.selected_option_id is not None:
            selected_opt = self.db.get(QuestionOption, req.selected_option_id)
            if selected_opt is None or selected_opt.question_id != req.question_id:
                raise ValidationError("Invalid option for this question")
            is_correct = selected_opt.is_correct
            correct_option_id = selected_opt.id
        else:
            # find the correct option for the response
            for opt in question.options:
                if opt.is_correct:
                    correct_option_id = opt.id
                    break

        answer = PracticeAnswer(
            session_id=session.id,
            question_id=req.question_id,
            selected_option_id=req.selected_option_id,
            is_correct=is_correct,
            time_taken_seconds=req.time_taken_seconds,
        )
        self.repo.create_answer(answer)
        self.repo.flush()

        # Update session counters
        session.question_count = max(session.question_count, 0)
        if is_correct:
            session.correct_count += 1
        elif req.selected_option_id is not None:
            session.incorrect_count += 1
        else:
            session.unattempted_count += 1

        # Track total time
        if req.time_taken_seconds:
            session.total_time_seconds = (session.total_time_seconds or 0) + req.time_taken_seconds

        self.repo.commit()

        return PracticeAnswerData(
            question_id=req.question_id,
            is_correct=is_correct,
            correct_option_id=correct_option_id,
            explanation=question.explanation,
        )

    # ============================================================ COMPLETE

    def complete_session(
        self, session_id: int, student: StudentProfile
    ) -> PracticeCompleteData:
        """Finalize a practice session and calculate the score."""
        session = self.repo.get_session(session_id)
        if session is None:
            raise NotFoundError(f"Session {session_id} not found")
        if session.student_id != student.id:
            raise ValidationError("Session does not belong to this student")
        if session.status != "IN_PROGRESS":
            raise ConflictError("Session already completed")

        # Calculate score
        total = session.correct_count + session.incorrect_count + session.unattempted_count
        if total == 0:
            total = session.question_count  # fallback
        score = round((session.correct_count / total) * 100) if total > 0 else 0
        accuracy = round((session.correct_count / total) * 100, 2) if total > 0 else 0

        # Finalize the session FIRST so badge/mission rules see the completed
        # session (docs/Phases.md §14: rewards reflect real activity).
        session.score = score
        session.xp_earned = 0
        session.status = "COMPLETED"
        session.completed_at = datetime.now(timezone.utc)
        self.repo.flush()

        # Phase 10: XP via the auditable ledger (same rule values as before),
        # streak update, mission progress, and badge evaluation.
        from app.services.gamification import (
            XP_COMPLETE_SESSION_BONUS,
            XP_CORRECT_ANSWER,
            XP_DAILY_QUIZ_BONUS,
            GamificationService,
        )

        gam = GamificationService(self.db)
        xp = session.correct_count * XP_CORRECT_ANSWER
        xp += XP_COMPLETE_SESSION_BONUS
        if session.mode == "DAILY_QUIZ":
            xp += XP_DAILY_QUIZ_BONUS

        gam.award_xp(
            student, xp, "PRACTICE_COMPLETE", reference_id=session.id,
            description=f"Practice session #{session.id} ({session.mode})",
        )
        gam.touch_streak(student)
        gam.update_mission_progress(student, "ANSWER_QUESTION", increment=session.correct_count + session.incorrect_count)
        gam.update_mission_progress(student, "COMPLETE_PRACTICE", increment=1)
        if session.mode == "DAILY_QUIZ":
            gam.update_mission_progress(student, "COMPLETE_DAILY_QUIZ", increment=1)
        gam.evaluate_badges(student)

        session.xp_earned = xp

        # Feature Group 9: readiness recomputed from real activity after events.
        from app.services.readiness import sync_profile_readiness

        sync_profile_readiness(self.db, student)

        self.repo.commit()

        return PracticeCompleteData(
            session_id=session.id,
            score=score,
            correct=session.correct_count,
            incorrect=session.incorrect_count,
            unattempted=session.unattempted_count,
            accuracy=accuracy,
            total_time_seconds=session.total_time_seconds or 0,
            xp_earned=xp,
        )

    # ============================================================ HISTORY

    def get_history(
        self, student: StudentProfile, page: int = 1, limit: int = 20
    ) -> PracticeHistoryData:
        offset = (page - 1) * limit
        sessions, total = self.repo.list_sessions(student.id, offset=offset, limit=limit)
        return PracticeHistoryData(
            sessions=[PracticeSessionSummary.model_validate(s) for s in sessions],
            total=total,
            page=page,
            limit=limit,
        )

    # ============================================================ PROGRESS

    def get_progress(self, student: StudentProfile) -> OverallProgressData:
        stats = self.repo.get_overall_stats(student.id)
        topic_progress = self.repo.get_topic_progress(student.id)
        session_count = self.repo.get_session_count(student.id)

        return OverallProgressData(
            total_questions_attempted=stats["total_questions_attempted"],
            total_correct=stats["total_correct"],
            total_incorrect=stats["total_incorrect"],
            overall_accuracy=stats["overall_accuracy"],
            total_sessions=session_count,
            topic_progress=[TopicProgressItem(**t) for t in topic_progress],
            xp=student.xp,
            level=student.level,
            current_streak=student.current_streak,
        )

    # ============================================================ DASHBOARD

    def get_dashboard(self, student: StudentProfile, user) -> DashboardData:
        stats = self.repo.get_overall_stats(student.id)
        topic_progress = self.repo.get_topic_progress(student.id)
        recent_sessions, _ = self.repo.list_sessions(student.id, offset=0, limit=5)

        return DashboardData(
            student_id=student.student_id,
            name=user.name,
            email=user.email,
            xp=student.xp,
            level=student.level,
            current_streak=student.current_streak,
            readiness_score=float(student.readiness_score),
            total_questions_attempted=stats["total_questions_attempted"],
            total_correct=stats["total_correct"],
            overall_accuracy=stats["overall_accuracy"],
            recent_sessions=[PracticeSessionSummary.model_validate(s) for s in recent_sessions],
            topic_progress=[TopicProgressItem(**t) for t in topic_progress],
        )

    # ============================================================ DAILY QUIZ

    def start_daily_quiz(self, student: StudentProfile) -> PracticeStartData:
        """Start or resume the student's daily quiz.

        Resume rule (audit fix): only a session still IN_PROGRESS resumes; a
        completed daily quiz is never handed back, so one quiz per day means
        one *playable* quiz per day. Sessions are created idempotently while
        in progress so repeated starts/refreshes are safe.
        """
        existing = self.repo.get_latest_daily_quiz_session(student.id)
        if existing and existing.status == "IN_PROGRESS":
            # Resume: return existing session questions.
            # The session's question set is only recorded via its answers, so
            # rebuild from answers; if the student refreshed before answering
            # anything there is nothing to rebuild — hand back an equivalent
            # fresh set of the same size so a mid-quiz refresh stays playable.
            questions = []
            for ans in existing.answers:
                q = self.db.get(Question, ans.question_id)
                if q:
                    questions.append(
                        QuestionForPractice(
                            id=q.id,
                            question_text=q.question_text,
                            question_type=q.question_type,
                            difficulty=q.difficulty,
                            options=[QuestionOptionOut.model_validate(o) for o in q.options],
                        )
                    )
            if not questions:
                questions = self.repo.get_random_questions(count=existing.question_count)
            return PracticeStartData(
                session_id=existing.id,
                mode="DAILY_QUIZ",
                topic_id=existing.topic_id,
                company_id=existing.company_id,
                difficulty=existing.difficulty,
                question_count=existing.question_count,
                questions=questions,
            )

        # Create new daily quiz: 10 random questions across all topics
        questions = self.repo.get_random_questions(count=10)
        if not questions:
            raise NotFoundError("No questions available for daily quiz")

        session = PracticeSession(
            student_id=student.id,
            mode="DAILY_QUIZ",
            question_count=len(questions),
            status="IN_PROGRESS",
        )
        self.repo.create_session(session)
        self.repo.commit()

        q_out = [
            QuestionForPractice(
                id=q.id,
                question_text=q.question_text,
                question_type=q.question_type,
                difficulty=q.difficulty,
                options=[QuestionOptionOut.model_validate(o) for o in q.options],
            )
            for q in questions
        ]

        return PracticeStartData(
            session_id=session.id,
            mode="DAILY_QUIZ",
            topic_id=None,
            company_id=None,
            difficulty=None,
            question_count=len(questions),
            questions=q_out,
        )

    # ============================================================ HELPERS

    @staticmethod
    def _calc_level(xp: int) -> int:
        """Determine the student's level from cumulative XP."""
        # Simple thresholds: L1=0, L2=100, L3=250, L4=450, ...
        thresholds = [0, 100, 250, 450, 700, 1000, 1400, 1850, 2350, 3000]
        level = 1
        for i, t in enumerate(thresholds):
            if xp >= t:
                level = i + 1
            else:
                break
        # beyond predefined thresholds, every 600 XP = +1 level
        if xp >= thresholds[-1]:
            extra = xp - thresholds[-1]
            level = len(thresholds) + (extra // 600)
        return level
