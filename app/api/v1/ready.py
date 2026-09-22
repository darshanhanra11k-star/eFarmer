from fastapi import APIRouter
from sqlalchemy import text

from app.core.exceptions import ServiceUnavailableError
from app.dependencies.db import SessionDep

router = APIRouter(tags=["Health"])


@router.get("/ready")
async def ready(session: SessionDep) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        raise ServiceUnavailableError() from None
    return {"status": "ready"}
