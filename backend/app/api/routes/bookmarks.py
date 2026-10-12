"""Bookmark endpoints (Feature Group 12 — Saved Questions)."""
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.db.session import get_db
from app.services.bookmark import BookmarkService
from app.utils.responses import success_response

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])


def _get_service(db: Session = Depends(get_db)) -> BookmarkService:
    return BookmarkService(db)


class BookmarkCreate(BaseModel):
    bookmark_type: str = Field(pattern=r"^(QUESTION|PROBLEM|CONCEPT)$")
    question_id: int | None = None
    problem_id: int | None = None
    note: str | None = Field(default=None, max_length=2000)


@router.get("")
def my_bookmarks(
    user: Annotated[object, Depends(require_student)],
    service: BookmarkService = Depends(_get_service),
):
    data = service.list_for_student(user.student_profile)
    return success_response(data=data, message="Bookmarks retrieved")


@router.post("", status_code=201)
def create_bookmark(
    req: BookmarkCreate,
    user: Annotated[object, Depends(require_student)],
    service: BookmarkService = Depends(_get_service),
):
    bookmark = service.add(
        user.student_profile,
        bookmark_type=req.bookmark_type,
        question_id=req.question_id,
        problem_id=req.problem_id,
        note=req.note,
    )
    return success_response(
        data={"id": bookmark.id, "bookmark_type": bookmark.bookmark_type,
              "question_id": bookmark.question_id, "problem_id": bookmark.problem_id},
        message="Bookmark saved",
        status_code=201,
    )


@router.delete("/{bookmark_id}")
def delete_bookmark(
    bookmark_id: int,
    user: Annotated[object, Depends(require_student)],
    service: BookmarkService = Depends(_get_service),
):
    service.remove(user.student_profile, bookmark_id)
    return success_response(data={"id": bookmark_id, "removed": True}, message="Bookmark removed")
