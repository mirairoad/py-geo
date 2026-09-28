from fastapi import APIRouter

router = APIRouter()


@router.get("/ready")
async def get_ready() -> dict[str, str]:
    return {"status": "ok"}
