from fastapi import APIRouter

from app.api.v1.capacity import router as capacity_router
from app.api.v1.centres import router as centres_router
from app.api.v1.farmers import router as farmers_router
from app.api.v1.health import router as health_router
from app.api.v1.procurement import router as procurement_router
from app.api.v1.queues import router as queues_router
from app.api.v1.ready import router as ready_router
from app.api.v1.tokens import router as tokens_router

router = APIRouter(prefix="/api/v1")

router.include_router(health_router)
router.include_router(ready_router)
router.include_router(farmers_router)
router.include_router(centres_router)
router.include_router(capacity_router)
router.include_router(queues_router)
router.include_router(tokens_router)
router.include_router(procurement_router)
