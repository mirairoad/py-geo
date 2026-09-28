import uvicorn


def run() -> None:
    uvicorn.run("server.app:create_app", port=3001, reload=True, factory=True)
