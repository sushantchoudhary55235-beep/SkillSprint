"""API router aggregation."""
from fastapi import APIRouter

from app.api.routes import admin, assessments, auth, content, health, students, teachers

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(students.router)
api_router.include_router(teachers.router)
api_router.include_router(admin.router)
api_router.include_router(content.router)
api_router.include_router(assessments.router)
