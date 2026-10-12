"""Assessment service: business logic for the assessment and testing system.

Phase 6 completion criteria (docs/Phases.md §11):
- Assessments can be created.
- Students can start assessments.
- Answers are recorded.
- Submission works.
- Scores are calculated.
- Results are stored.
- Assessment history works.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.assessment import Answer, Assessment, AssessmentQuestion, Attempt
from app.models.content import Topic
from app.models.profile import StudentProfile
from app.models.question import Question, QuestionOption
from app.repositories.assessment import AssessmentRepository
from app.schemas.assessment import (
    AttemptAnswerRequest,
    AttemptAnswerResponse,
    AttemptHistoryItem,
    AttemptResultResponse,
    AttemptStartResponse,
    AttemptSubmitResponse,
    AssessmentCreate,
    AssessmentListResponse,
    AssessmentRead,
    AssessmentReadDetail,
    AssessmentUpdate,
    QuestionForAttempt,
)


class AssessmentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = AssessmentRepository(db)

    # ============================================================ ADMIN CRUD

    def create(self, data: AssessmentCreate, user) -> AssessmentReadDetail:
        """Admin creates an assessment with associated questions."""
        # Validate all question IDs exist and are approved
        for qid in data.question_ids:
            q = self.db.get(Question, qid)
            if q is None:
                raise NotFoundError(f"Question {qid} not found")
            if q.status != "approved":
                raise ValidationError(f"Question {qid} is not approved")

        assessment = Assessment(
            title=data.title,
            assessment_type=data.assessment_type,
            duration_minutes=data.duration_minutes,
            company_id=data.company_id,
            question_count=len(data.question_ids),
            created_by=user.id,
            is_active=True,
        )
        self.repo.create_assessment(assessment)

        for i, qid in enumerate(data.question_ids, 1):
            aq = AssessmentQuestion(
                assessment_id=assessment.id,
                question_id=qid,
                question_order=i,
                marks=1,
            )
            self.repo.add_assessment_question(aq)

        self.repo.commit()
        self.repo.refresh(assessment)
        question_ids = self.repo.get_assessment_question_ids(assessment.id)
        return AssessmentReadDetail(
            id=assessment.id,
            title=assessment.title,
            assessment_type=assessment.assessment_type,
            duration_minutes=assessment.duration_minutes,
            question_count=assessment.question_count,
            company_id=assessment.company_id,
            is_active=assessment.is_active,
            created_at=assessment.created_at,
            question_ids=question_ids,
        )

    def update(self, assessment_id: int, data: AssessmentUpdate) -> Assessment:
        assessment = self.repo.get_assessment(assessment_id)
        if assessment is None:
            raise NotFoundError(f"Assessment {assessment_id} not found")

        update_data = data.model_dump(exclude_unset=True)
        if "question_ids" in update_data:
            qids = update_data.pop("question_ids")
            # Validate new question IDs
            for qid in qids:
                q = self.db.get(Question, qid)
                if q is None or q.status != "approved":
                    raise ValidationError(f"Question {qid} is not valid/approved")
            # Remove old assessment questions
            old_aqs = list(self.db.scalars(
                select(AssessmentQuestion).where(
                    AssessmentQuestion.assessment_id == assessment_id
                )
            ).all())
            for aq in old_aqs:
                self.db.delete(aq)
            # Add new
            for i, qid in enumerate(qids, 1):
                aq = AssessmentQuestion(
                    assessment_id=assessment_id,
                    question_id=qid,
                    question_order=i,
                    marks=1,
                )
                self.repo.add_assessment_question(aq)
            assessment.question_count = len(qids)

        for field, value in update_data.items():
            setattr(assessment, field, value)

        self.repo.commit()
        return assessment

    def list_all(self, page: int = 1, limit: int = 20) -> AssessmentListResponse:
        offset = (page - 1) * limit
        assessments, total = self.repo.list_all_assessments(offset=offset, limit=limit)
        return AssessmentListResponse(
            assessments=[AssessmentRead.model_validate(a) for a in assessments],
            total=total,
            page=page,
            limit=limit,
        )

    def list_active(self, page: int = 1, limit: int = 20) -> AssessmentListResponse:
        offset = (page - 1) * limit
        assessments, total = self.repo.list_active_assessments(offset=offset, limit=limit)
        return AssessmentListResponse(
            assessments=[AssessmentRead.model_validate(a) for a in assessments],
            total=total,
            page=page,
            limit=limit,
        )

    def get_detail(self, assessment_id: int) -> AssessmentReadDetail:
        assessment = self.repo.get_assessment(assessment_id)
        if assessment is None:
            raise NotFoundError(f"Assessment {assessment_id} not found")
        question_ids = self.repo.get_assessment_question_ids(assessment_id)
        return AssessmentReadDetail(
            id=assessment.id,
            title=assessment.title,
            assessment_type=assessment.assessment_type,
            duration_minutes=assessment.duration_minutes,
            question_count=assessment.question_count,
            company_id=assessment.company_id,
            is_active=assessment.is_active,
            created_at=assessment.created_at,
            question_ids=question_ids,
        )

    # ============================================================ STUDENT ATTEMPT

    def start_attempt(
        self, assessment_id: int, student: StudentProfile
    ) -> AttemptStartResponse:
        """Start a new attempt for an active assessment."""
        assessment = self.repo.get_assessment(assessment_id)
        if assessment is None or not assessment.is_active:
            raise NotFoundError(f"Assessment {assessment_id} not found or inactive")

        # Check for existing active attempt
        existing = self.repo.get_active_attempt(student.id, assessment_id)
        if existing:
            raise ConflictError("You already have an in-progress attempt for this assessment")

        # Create attempt
        attempt = Attempt(
            student_id=student.id,
            assessment_id=assessment_id,
            started_at=datetime.now(timezone.utc),
            status="IN_PROGRESS",
        )
        self.repo.create_attempt(attempt)

        # Load questions (snapshot at attempt creation)
        question_ids = self.repo.get_assessment_question_ids(assessment_id)
        questions = []
        for qid in question_ids:
            q = self.db.get(Question, qid)
            if q:
                opts = [
                    {"id": o.id, "option_text": o.option_text, "option_order": o.option_order}
                    for o in q.options
                ]
                questions.append({
                    "id": q.id,
                    "question_text": q.question_text,
                    "question_type": q.question_type,
                    "difficulty": q.difficulty,
                    "options": opts,
                })

        self.repo.commit()

        return AttemptStartResponse(
            attempt_id=attempt.id,
            assessment_id=assessment_id,
            started_at=attempt.started_at,
            duration_minutes=assessment.duration_minutes,
            question_count=len(questions),
            questions=questions,
        )

    def submit_answer(
        self,
        attempt_id: int,
        data: AttemptAnswerRequest,
        student: StudentProfile,
    ) -> AttemptAnswerResponse:
        """Submit an answer during an active attempt with timer enforcement."""
        attempt = self.repo.get_attempt(attempt_id)
        if attempt is None:
            raise NotFoundError(f"Attempt {attempt_id} not found")
        if attempt.student_id != student.id:
            raise ForbiddenError("This attempt does not belong to you")
        if attempt.status != "IN_PROGRESS":
            raise ConflictError("Attempt is no longer in progress")

        # Timer enforcement
        assessment = self.db.get(Assessment, attempt.assessment_id)
        started = attempt.started_at.replace(tzinfo=timezone.utc) if attempt.started_at.tzinfo is None else attempt.started_at
        deadline = started + timedelta(minutes=assessment.duration_minutes)
        now = datetime.now(timezone.utc)
        if now > deadline:
            attempt.status = "EXPIRED"
            self.repo.commit()
            raise ConflictError("Assessment time has expired")

        # Validate question belongs to this assessment
        assessment_qids = set(self.repo.get_assessment_question_ids(attempt.assessment_id))
        if data.question_id not in assessment_qids:
            raise ValidationError("Question does not belong to this assessment")

        # Server-side correctness evaluation
        question = self.db.get(Question, data.question_id)
        is_correct = False
        correct_option_id = None
        for opt in question.options:
            if opt.is_correct:
                correct_option_id = opt.id
                break

        if data.selected_option_id is not None:
            selected_opt = self.db.get(QuestionOption, data.selected_option_id)
            if selected_opt is None or selected_opt.question_id != data.question_id:
                raise ValidationError("Invalid option for this question")
            is_correct = selected_opt.is_correct

        # Upsert answer
        existing = self.repo.get_existing_answer(attempt_id, data.question_id)
        if existing:
            existing.selected_option_id = data.selected_option_id
            existing.is_correct = is_correct
            existing.time_taken_seconds = data.time_taken_seconds
            answer = existing
        else:
            answer = Answer(
                attempt_id=attempt_id,
                question_id=data.question_id,
                selected_option_id=data.selected_option_id,
                is_correct=is_correct,
                time_taken_seconds=data.time_taken_seconds,
            )
            self.repo.create_answer(answer)

        self.repo.commit()

        return AttemptAnswerResponse(
            question_id=data.question_id,
            is_correct=is_correct,
            correct_option_id=correct_option_id,
        )

    def submit_attempt(
        self, attempt_id: int, student: StudentProfile
    ) -> AttemptSubmitResponse:
        """Finalize and score an attempt."""
        attempt = self.repo.get_attempt(attempt_id)
        if attempt is None:
            raise NotFoundError(f"Attempt {attempt_id} not found")
        if attempt.student_id != student.id:
            raise ForbiddenError("This attempt does not belong to you")
        if attempt.status == "SUBMITTED":
            raise ConflictError("Attempt already submitted")
        if attempt.status == "EXPIRED":
            raise ConflictError("Attempt has expired")

        # Auto-expire check
        assessment = self.db.get(Assessment, attempt.assessment_id)
        started = attempt.started_at.replace(tzinfo=timezone.utc) if attempt.started_at.tzinfo is None else attempt.started_at
        deadline = started + timedelta(minutes=assessment.duration_minutes)
        now = datetime.now(timezone.utc)
        if now > deadline:
            attempt.status = "EXPIRED"
            self.repo.commit()
            raise ConflictError("Assessment time has expired")

        # Calculate scores
        total_questions = assessment.question_count
        correct = sum(1 for a in attempt.answers if a.is_correct)
        incorrect = sum(1 for a in attempt.answers if a.selected_option_id is not None and not a.is_correct)
        unattempted = total_questions - correct - incorrect
        score = round((correct / total_questions) * 100, 2) if total_questions > 0 else 0
        accuracy = round((correct / (correct + incorrect)) * 100, 2) if (correct + incorrect) > 0 else 0

        started = attempt.started_at.replace(tzinfo=timezone.utc) if attempt.started_at.tzinfo is None else attempt.started_at
        time_taken = int((now - started).total_seconds())

        attempt.score = score
        attempt.total_marks = total_questions
        attempt.correct_count = correct
        attempt.incorrect_count = incorrect
        attempt.unattempted_count = unattempted
        attempt.accuracy = accuracy
        attempt.time_taken_seconds = time_taken
        attempt.submitted_at = now
        attempt.status = "SUBMITTED"

        # Calculate topic performance
        topic_perf = self._calculate_topic_performance(attempt)

        # Phase 7: record snapshot + refresh persisted topic aggregates
        from app.services.performance import PerformanceService

        PerformanceService(self.db).snapshot_after_assessment(
            student,
            assessment_id=attempt.assessment_id,
            score=score,
            accuracy=accuracy,
        )

        # Phase 10: XP, streak, missions, badges from validated server events.
        from app.services.gamification import XP_ASSESSMENT_COMPLETE, GamificationService

        gam = GamificationService(self.db)
        gam.award_xp(
            student, XP_ASSESSMENT_COMPLETE, "ASSESSMENT_COMPLETE",
            reference_id=attempt.id, description=f"Assessment attempt #{attempt.id}",
        )
        gam.touch_streak(student)
        gam.update_mission_progress(student, "COMPLETE_ASSESSMENT", increment=1)
        gam.update_mission_progress(student, "ANSWER_QUESTION", increment=correct + incorrect)
        gam.evaluate_badges(student)

        # Feature Group 9: readiness recomputed from real activity after events.
        from app.services.readiness import sync_profile_readiness

        sync_profile_readiness(self.db, student)

        self.repo.commit()

        return AttemptSubmitResponse(
            attempt_id=attempt.id,
            score=score,
            total_questions=total_questions,
            correct=correct,
            incorrect=incorrect,
            unattempted=unattempted,
            accuracy=accuracy,
            time_taken_seconds=time_taken,
            topic_performance=topic_perf,
        )

    def get_result(
        self, attempt_id: int, student: StudentProfile
    ) -> AttemptResultResponse:
        """Get full result of a completed attempt."""
        attempt = self.repo.get_attempt(attempt_id)
        if attempt is None:
            raise NotFoundError(f"Attempt {attempt_id} not found")
        if attempt.student_id != student.id:
            raise ForbiddenError("This attempt does not belong to you")

        assessment = self.db.get(Assessment, attempt.assessment_id)
        topic_perf = self._calculate_topic_performance(attempt) if attempt.status in ("SUBMITTED", "EXPIRED") else []

        return AttemptResultResponse(
            attempt_id=attempt.id,
            assessment_id=attempt.assessment_id,
            assessment_title=assessment.title,
            status=attempt.status,
            score=float(attempt.score) if attempt.score is not None else 0,
            total_questions=assessment.question_count,
            correct_count=attempt.correct_count,
            incorrect_count=attempt.incorrect_count,
            unattempted_count=attempt.unattempted_count,
            accuracy=float(attempt.accuracy) if attempt.accuracy is not None else 0,
            started_at=attempt.started_at,
            submitted_at=attempt.submitted_at,
            time_taken_seconds=attempt.time_taken_seconds,
            topic_performance=topic_perf,
        )

    def get_history(
        self, student: StudentProfile, page: int = 1, limit: int = 20
    ) -> list[AttemptHistoryItem]:
        """Get student's attempt history."""
        offset = (page - 1) * limit
        rows, total = self.repo.list_student_attempts(student.id, offset=offset, limit=limit)
        return [
            AttemptHistoryItem(
                id=r["attempt"].id,
                assessment_id=r["attempt"].assessment_id,
                assessment_title=r["assessment_title"],
                score=float(r["attempt"].score) if r["attempt"].score is not None else None,
                correct_count=r["attempt"].correct_count,
                incorrect_count=r["attempt"].incorrect_count,
                unattempted_count=r["attempt"].unattempted_count,
                accuracy=float(r["attempt"].accuracy) if r["attempt"].accuracy is not None else None,
                status=r["attempt"].status,
                started_at=r["attempt"].started_at,
                submitted_at=r["attempt"].submitted_at,
            )
            for r in rows
        ]

    # ============================================================ HELPERS

    def _calculate_topic_performance(self, attempt: Attempt) -> list[dict]:
        """Break down scores by topic for the result page."""
        topic_stats: dict[int, dict] = {}
        for ans in attempt.answers:
            q = self.db.get(Question, ans.question_id)
            if q is None or q.topic_id is None:
                continue
            tid = q.topic_id
            if tid not in topic_stats:
                topic_stats[tid] = {"total": 0, "correct": 0}
            topic_stats[tid]["total"] += 1
            if ans.is_correct:
                topic_stats[tid]["correct"] += 1

        result = []
        for tid, stats in topic_stats.items():
            topic = self.db.get(Topic, tid)
            acc = round((stats["correct"] / stats["total"]) * 100, 2) if stats["total"] > 0 else 0
            result.append({
                "topic_id": tid,
                "topic_name": topic.name if topic else "Unknown",
                "correct": stats["correct"],
                "total": stats["total"],
                "accuracy": acc,
            })
        return result
