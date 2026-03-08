"""Health-check endpoints for uptime and readiness probes."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from core.concurrency import concurrency_manager
from utils.log import log_warning

router = APIRouter(tags=["health"])


class ComponentHealth(BaseModel):
    status: str  # "ok" | "degraded" | "down"
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    status: str  # "healthy" | "degraded" | "unhealthy"
    database: ComponentHealth
    redis: ComponentHealth
    model: ComponentHealth


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """System health probe checking database, Redis, and LLM model."""
    def _query():
        db_health = _check_database()
        redis_health = _check_redis()
        model_health = _check_model()

        # Overall status: unhealthy if DB is down, degraded if redis/model is down
        if db_health.status == "down":
            overall = "unhealthy"
        elif redis_health.status == "down" or model_health.status == "down":
            overall = "degraded"
        else:
            overall = "healthy"

        return HealthResponse(
            status=overall,
            database=db_health,
            redis=redis_health,
            model=model_health,
        )

    return await concurrency_manager.run_in_thread(_query)


def _check_database() -> ComponentHealth:
    try:
        from infrastructure.database.session import get_engine
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return ComponentHealth(status="ok")
    except Exception as e:
        log_warning(f"Health: DB check failed: {e}")
        return ComponentHealth(status="down", detail=str(e)[:200])


def _check_redis() -> ComponentHealth:
    try:
        from infrastructure.cache.redis_cache import redis_tool
        client = redis_tool._get_client()
        client.ping()
        return ComponentHealth(status="ok")
    except Exception as e:
        log_warning(f"Health: Redis check failed: {e}")
        return ComponentHealth(status="down", detail=str(e)[:200])


def _check_model() -> ComponentHealth:
    try:
        from infrastructure.llm import form
        if form.SELECTED_MODEL and form.SELECTED_MODEL.llm:
            return ComponentHealth(status="ok", detail=form.SELECTED_MODEL.model_name)
        return ComponentHealth(status="down", detail="No model registered")
    except Exception as e:
        log_warning(f"Health: Model check failed: {e}")
        return ComponentHealth(status="down", detail=str(e)[:200])
