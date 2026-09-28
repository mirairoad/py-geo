from fastapi import FastAPI

from server import apis


def create_app() -> FastAPI:
    app = FastAPI(title="py-geo")
    app.include_router(apis.router, prefix="/api")
    return app
