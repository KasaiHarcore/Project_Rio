"""API router registry — collects all route modules into a single v1 router."""

from fastapi import APIRouter

from routers.auth import router as auth_router
from routers.chat import router as chat_router
from routers.collection import router as collection_router
from routers.dashboard import router as dashboard_router
from routers.emotional import router as emotional_router
from routers.rio_response import router as rio_response_router
from routers.health import router as health_router
from routers.knowledge import router as knowledge_router
from routers.onboarding import router as onboarding_router
from routers.mission import router as mission_router
from routers.note import router as note_router
from routers.sql_approval import router as sql_approval_router
from routers.artifact import router as artifact_router
from routers.logs import router as logs_router
from routers.settings import router as settings_router
from routers.oauth import router as oauth_router
from routers.jwks import router as jwks_router
from routers.websocket import router as websocket_router
from routers.admin import router as admin_router
from routers.search import router as search_router
from routers.ingest import router as ingest_router
from routers.note_link import router as note_link_router
from routers.os_control import router as os_control_router

v1_router = APIRouter()

v1_router.include_router(auth_router)
v1_router.include_router(oauth_router)
v1_router.include_router(chat_router)
v1_router.include_router(dashboard_router)
v1_router.include_router(emotional_router)
v1_router.include_router(rio_response_router)
v1_router.include_router(health_router)
v1_router.include_router(knowledge_router)
v1_router.include_router(onboarding_router)
v1_router.include_router(mission_router)
v1_router.include_router(note_router)
v1_router.include_router(collection_router)
v1_router.include_router(sql_approval_router)
v1_router.include_router(artifact_router)
v1_router.include_router(logs_router)
v1_router.include_router(settings_router)
v1_router.include_router(jwks_router)
v1_router.include_router(websocket_router)
v1_router.include_router(admin_router)
v1_router.include_router(search_router)
v1_router.include_router(ingest_router)
v1_router.include_router(note_link_router)
v1_router.include_router(os_control_router)

__all__ = ["v1_router"]
