"""Gamification endpoints: XP/level/streak summary, missions, badges, leaderboard, activity.

Security: there is NO endpoint accepting client-supplied XP. All XP originates
from server-side events (practice/assessment completion, mission/badge rules).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_student
from app.db.session import get_db
from app.services.gamification import GamificationService
from app.services.leaderboard import PERIODS, LeaderboardService
from app.utils.responses import success_response

router = APIRouter(prefix="/gamification", tags=["gamification"])


def _get_service(db: Session = Depends(get_db)) -> GamificationService:
    return GamificationService(db)


def _get_leaderboard_service(db: Session = Depends(get_db)) -> LeaderboardService:
    return LeaderboardService(db)


@router.get("/me")
def my_gamification(
    user: Annotated[object, Depends(require_student)],
    service: GamificationService = Depends(_get_service),
):
    student = user.student_profile
    return success_response(
        data={
            **service.xp_summary(student),
            "current_streak": student.current_streak,
            "longest_streak": student.longest_streak,
        },
        message="Gamification summary retrieved",
    )


@router.get("/missions")
def my_missions(
    user: Annotated[object, Depends(require_student)],
    service: GamificationService = Depends(_get_service),
):
    data = service.list_student_missions(user.student_profile)
    return success_response(data=data, message="Missions retrieved")


@router.get("/badges")
def my_badges(
    user: Annotated[object, Depends(require_student)],
    service: GamificationService = Depends(_get_service),
):
    data = service.list_student_badges(user.student_profile)
    return success_response(data=data, message="Badges retrieved")


@router.get("/badges/catalog")
def badge_catalog(
    user: Annotated[object, Depends(require_student)],
    service: GamificationService = Depends(_get_service),
):
    """Full badge catalogue so the UI can show locked badges with unlock rules."""
    from sqlalchemy import select

    from app.models.gamification import Badge

    badges = service.db.scalars(select(Badge).where(Badge.is_active.is_(True)).order_by(Badge.id)).all()
    data = [
        {
            "id": b.id,
            "name": b.name,
            "description": b.description,
            "icon": b.icon,
            "criteria_type": b.criteria_type,
            "criteria_value": b.criteria_value,
            "xp_reward": b.xp_reward,
        }
        for b in badges
    ]
    return success_response(data=data, message="Badge catalogue retrieved")


@router.get("/activity")
def my_activity(
    user: Annotated[object, Depends(require_student)],
    service: GamificationService = Depends(_get_service),
    limit: int = Query(default=10, ge=1, le=50),
):
    events = service.recent_activity(user.student_profile, limit=limit)
    data = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "reference_id": e.reference_id,
            "metadata": e.metadata_json,
            "created_at": e.created_at,
        }
        for e in events
    ]
    return success_response(data=data, message="Activity retrieved")


@router.get("/leaderboard")
def leaderboard(
    user: Annotated[object, Depends(require_student)],
    service: LeaderboardService = Depends(_get_leaderboard_service),
    period: str = Query(default="WEEKLY", pattern=f"^({'|'.join(PERIODS)})$"),
    limit: int = Query(default=25, ge=1, le=100),
):
    data = service.get(period, limit=limit)
    return success_response(data=data, message="Leaderboard retrieved")


@router.get("/leaderboard/me")
def my_rank(
    user: Annotated[object, Depends(require_student)],
    service: LeaderboardService = Depends(_get_leaderboard_service),
    period: str = Query(default="WEEKLY", pattern=f"^({'|'.join(PERIODS)})$"),
):
    data = service.my_rank(user.student_profile, period)
    return success_response(data=data, message="Rank retrieved")
