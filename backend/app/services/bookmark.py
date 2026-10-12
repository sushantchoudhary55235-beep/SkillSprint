"""Bookmarks service (Feature Group 12 — Saved Questions).

Lightweight saved-items layer over existing questions/problems. The underlying
content is referenced by id, never copied. All access is ownership-checked.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.bookmark import Bookmark
from app.models.coding import CodingProblem
from app.models.profile import StudentProfile
from app.models.question import Question, QuestionOption

VALID_TYPES = ("QUESTION", "PROBLEM", "CONCEPT")


class BookmarkService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, student: StudentProfile, *, bookmark_type: str, question_id: int | None,
            problem_id: int | None, note: str | None) -> Bookmark:
        if bookmark_type not in VALID_TYPES:
            raise ValidationError(f"bookmark_type must be one of {VALID_TYPES}")

        # Validate targets exist (ownership not required — questions/problems are shared content).
        if bookmark_type == "QUESTION" or question_id is not None:
            q = self.db.get(Question, question_id)
            if q is None:
                raise NotFoundError(f"Question {question_id} not found")
        if bookmark_type == "PROBLEM" or problem_id is not None:
            p = self.db.get(CodingProblem, problem_id)
            if p is None:
                raise NotFoundError(f"Coding problem {problem_id} not found")
        if bookmark_type == "CONCEPT" and not (note or "").strip():
            raise ValidationError("Concept bookmarks require a note")

        existing = self.db.scalar(
            select(Bookmark).where(
                Bookmark.student_id == student.id,
                Bookmark.bookmark_type == bookmark_type,
                Bookmark.question_id == question_id,
                Bookmark.problem_id == problem_id,
            )
        )
        if existing is not None:
            return existing  # idempotent re-save

        bookmark = Bookmark(
            student_id=student.id,
            bookmark_type=bookmark_type,
            question_id=question_id,
            problem_id=problem_id,
            note=(note or "").strip() or None,
        )
        self.db.add(bookmark)
        self.db.commit()
        self.db.refresh(bookmark)
        return bookmark

    def remove(self, student: StudentProfile, bookmark_id: int) -> None:
        bookmark = self.db.get(Bookmark, bookmark_id)
        if bookmark is None or bookmark.student_id != student.id:
            raise NotFoundError(f"Bookmark {bookmark_id} not found")
        self.db.delete(bookmark)
        self.db.commit()

    def list_for_student(self, student: StudentProfile) -> list[dict]:
        rows = self.db.execute(
            select(Bookmark).where(Bookmark.student_id == student.id).order_by(Bookmark.id.desc())
        ).scalars().all()

        question_ids = [b.question_id for b in rows if b.question_id]
        problem_ids = [b.problem_id for b in rows if b.problem_id]

        questions: dict[int, Question] = {}
        if question_ids:
            for q in self.db.scalars(select(Question).where(Question.id.in_(question_ids))):
                questions[q.id] = q
        problems: dict[int, CodingProblem] = {}
        if problem_ids:
            for p in self.db.scalars(select(CodingProblem).where(CodingProblem.id.in_(problem_ids))):
                problems[p.id] = p

        out = []
        for b in rows:
            item: dict = {
                "id": b.id,
                "bookmark_type": b.bookmark_type,
                "note": b.note,
                "created_at": b.created_at,
                "question_id": b.question_id,
                "problem_id": b.problem_id,
            }
            if b.question_id and b.question_id in questions:
                q = questions[b.question_id]
                correct_opt = next(
                    (o.option_text for o in q.options if o.is_correct), None
                )
                item.update({
                    "question_text": q.question_text,
                    "topic_id": q.topic_id,
                    "difficulty": q.difficulty,
                    "explanation": q.explanation,
                    "correct_answer": correct_opt,
                })
            if b.problem_id and b.problem_id in problems:
                p = problems[b.problem_id]
                item.update({
                    "problem_title": p.title,
                    "problem_difficulty": p.difficulty,
                })
            out.append(item)
        return out

    def count(self, student: StudentProfile) -> int:
        return self.db.scalar(
            select(func.count(Bookmark.id)).where(Bookmark.student_id == student.id)
        ) or 0
