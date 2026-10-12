"""API router aggregation."""
from fastapi import APIRouter

from app.api.routes import (
    account,
    adaptive,
    admin,
    ai,
    assessments,
    auth,
    bookmarks,
    coding,
    coaching,
    content,
    gamification,
    health,
    interview,
    performance,
    recommendations,
    roadmap,
    students,
    teachers,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(students.router)
api_router.include_router(teachers.router)
api_router.include_router(admin.router)
api_router.include_router(content.router)
api_router.include_router(assessments.router)
api_router.include_router(performance.router)
api_router.include_router(recommendations.router)
api_router.include_router(roadmap.router)
api_router.include_router(gamification.router)
api_router.include_router(coding.router)
api_router.include_router(ai.router)
api_router.include_router(coaching.router)
api_router.include_router(adaptive.router)
api_router.include_router(bookmarks.router)
api_router.include_router(interview.router)
api_router.include_router(account.router)
