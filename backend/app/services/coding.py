"""Coding Practice System (docs/Phases.md §15 — Phase 11).

Flow: browse problems → open problem → write code → run/submit →
execute against test cases (isolated) → verdict → submission history.

The verdict is decided ONLY by the backend executor+judge; the frontend
never determines correctness. Hidden test cases are never exposed.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.coding import CodingProblem, CodeSubmission, TestCase
from app.models.profile import StudentProfile
from app.schemas.coding import (
    CodingProblemDetail,
    CodingProblemListItem,
    SubmissionResultOut,
)
from app.services.code_executor import judge_submission


class CodingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ============================================================ BROWSE

    def list_problems(
        self,
        difficulty: str | None = None,
        topic_id: int | None = None,
        student: StudentProfile | None = None,
        page: int = 1,
        limit: int = 50,
    ) -> dict:
        """Paginated problem list with per-student solved flags (Phase 15.8)."""
        stmt = select(CodingProblem)
        count_stmt = select(func.count(CodingProblem.id))
        if difficulty:
            stmt = stmt.where(CodingProblem.difficulty == difficulty)
            count_stmt = count_stmt.where(CodingProblem.difficulty == difficulty)
        if topic_id:
            stmt = stmt.where(CodingProblem.topic_id == topic_id)
            count_stmt = count_stmt.where(CodingProblem.topic_id == topic_id)

        total = self.db.scalar(count_stmt) or 0
        problems = list(self.db.scalars(
            stmt.order_by(CodingProblem.id).offset((page - 1) * limit).limit(limit)
        ).all())

        solved_ids: set[int] = set()
        if student is not None and problems:
            solved_ids = set(self.db.scalars(
                select(CodeSubmission.problem_id).where(
                    CodeSubmission.student_id == student.id,
                    CodeSubmission.status == "ACCEPTED",
                    CodeSubmission.problem_id.in_([p.id for p in problems]),
                )
            ).all())
        items = [
            {
                **CodingProblemListItem.model_validate(p).model_dump(),
                "solved": p.id in solved_ids,
            }
            for p in problems
        ]
        return {"problems": items, "total": total, "page": page, "limit": limit}

    def get_problem(self, problem_id: int, student: StudentProfile | None = None) -> CodingProblemDetail:
        problem = self.db.get(CodingProblem, problem_id)
        if problem is None:
            raise NotFoundError(f"Coding problem {problem_id} not found")
        # Only visible (sample) test cases are exposed to students.
        samples = list(self.db.scalars(
            select(TestCase).where(
                TestCase.problem_id == problem_id,
                TestCase.is_hidden.is_(False),
            ).order_by(TestCase.id)
        ).all())
        solved = False
        if student is not None:
            solved = self.db.scalar(
                select(CodeSubmission.id).where(
                    CodeSubmission.student_id == student.id,
                    CodeSubmission.problem_id == problem_id,
                    CodeSubmission.status == "ACCEPTED",
                )
            ) is not None
        return CodingProblemDetail(
            id=problem.id,
            title=problem.title,
            description=problem.description,
            difficulty=problem.difficulty,
            topic_id=problem.topic_id,
            input_format=problem.input_format,
            output_format=problem.output_format,
            constraints=problem.constraints,
            sample_test_cases=samples,
            solved=solved,
        )

    # ============================================================ SUBMIT

    def submit(
        self, problem_id: int, student: StudentProfile, language: str, source_code: str
    ) -> SubmissionResultOut:
        problem = self.db.get(CodingProblem, problem_id)
        if problem is None:
            raise NotFoundError(f"Coding problem {problem_id} not found")

        test_cases = list(self.db.scalars(
            select(TestCase).where(TestCase.problem_id == problem_id).order_by(TestCase.id)
        ).all())
        if not test_cases:
            raise ValidationError("Problem has no test cases configured")

        # Record the submission first (audit trail), then judge it.
        submission = CodeSubmission(
            student_id=student.id,
            problem_id=problem_id,
            language=language,
            source_code=source_code,
            status="RUNNING",
            total_test_cases=len(test_cases),
        )
        self.db.add(submission)
        self.db.flush()

        verdict = judge_submission(language, source_code, test_cases)

        submission.status = verdict["status"]
        submission.passed_test_cases = verdict["passed"]
        submission.execution_time_ms = verdict["time_ms"]
        submission.error_message = verdict["error_message"]
        self.db.commit()
        self.db.refresh(submission)

        return SubmissionResultOut(
            id=submission.id,
            problem_id=problem_id,
            language=language,
            status=submission.status,
            passed_test_cases=submission.passed_test_cases,
            total_test_cases=submission.total_test_cases,
            execution_time_ms=submission.execution_time_ms,
            error_message=submission.error_message,
            results=verdict["results"],
        )

    # ============================================================ HISTORY

    def submission_history(
        self,
        student: StudentProfile,
        problem_id: int | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> dict:
        """Paginated submission history (Phase 15.8)."""
        stmt = select(CodeSubmission).where(CodeSubmission.student_id == student.id)
        count_stmt = select(func.count(CodeSubmission.id)).where(
            CodeSubmission.student_id == student.id
        )
        if problem_id:
            stmt = stmt.where(CodeSubmission.problem_id == problem_id)
            count_stmt = count_stmt.where(CodeSubmission.problem_id == problem_id)

        total = self.db.scalar(count_stmt) or 0
        rows = list(self.db.scalars(
            stmt.order_by(CodeSubmission.id.desc()).offset((page - 1) * limit).limit(limit)
        ).all())
        return {
            "submissions": [
                {
                    "id": s.id,
                    "problem_id": s.problem_id,
                    "language": s.language,
                    "status": s.status,
                    "passed_test_cases": s.passed_test_cases,
                    "total_test_cases": s.total_test_cases,
                    "created_at": s.created_at,
                }
                for s in rows
            ],
            "total": total,
            "page": page,
            "limit": limit,
        }

    # ============================================================ PERFORMANCE

    def performance(self, student: StudentProfile) -> dict:
        """Coding stats feeding Phase 7/personalization."""
        attempted = self.db.scalar(
            select(func.count(func.distinct(CodeSubmission.problem_id))).where(
                CodeSubmission.student_id == student.id)
        ) or 0
        solved = self.db.scalar(
            select(func.count(func.distinct(CodeSubmission.problem_id))).where(
                CodeSubmission.student_id == student.id,
                CodeSubmission.status == "ACCEPTED")
        ) or 0
        total_subs = self.db.scalar(
            select(func.count(CodeSubmission.id)).where(
                CodeSubmission.student_id == student.id)
        ) or 0
        accepted = self.db.scalar(
            select(func.count(CodeSubmission.id)).where(
                CodeSubmission.student_id == student.id,
                CodeSubmission.status == "ACCEPTED")
        ) or 0

        by_difficulty: dict[str, dict] = {}
        problems = self.db.scalars(select(CodingProblem)).all()
        difficulty_map = {p.id: p.difficulty for p in problems}
        solved_rows = self.db.execute(
            select(CodeSubmission.problem_id, func.count(func.distinct(CodeSubmission.problem_id)))
            .where(CodeSubmission.student_id == student.id, CodeSubmission.status == "ACCEPTED")
            .group_by(CodeSubmission.problem_id)
        ).all()
        solved_by_diff: dict[str, int] = {}
        for pid, _count in solved_rows:
            diff = difficulty_map.get(pid)
            if diff:
                solved_by_diff[diff] = solved_by_diff.get(diff, 0) + 1
        for diff in ("EASY", "MEDIUM", "HARD"):
            total_in_diff = sum(1 for d in difficulty_map.values() if d == diff)
            if total_in_diff:
                by_difficulty[diff.lower()] = {
                    "solved": solved_by_diff.get(diff, 0),
                    "total": total_in_diff,
                }

        return {
            "problems_attempted": attempted,
            "problems_solved": solved,
            "pass_rate": round(accepted / total_subs * 100, 2) if total_subs else None,
            "total_submissions": total_subs,
            "by_difficulty": by_difficulty,
        }
