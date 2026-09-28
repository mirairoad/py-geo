from fastapi import APIRouter

from . import health, ready

router = APIRouter()

router.include_router(health.router)
router.include_router(ready.router)
