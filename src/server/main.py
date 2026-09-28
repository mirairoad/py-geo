import uvicorn

from internals.config import Settings


def run() -> None:
    settings = Settings()

    uvicorn.run(
        "server.app:create_app", host=settings.host, port=settings.port, reload=True, factory=True
    )
