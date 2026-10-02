import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .api.routes import router
from .storage.sqlite import Store, error_body, new_id


def create_app(sqlite_path: str | Path | None = None, *, db_path: str | Path | None = None) -> FastAPI:
    application = FastAPI(title="逃离校园实验室", version="0.1.0")
    default_path = Path(__file__).resolve().parents[2] / "data" / "game.sqlite"
    if sqlite_path is not None and db_path is not None:
        raise ValueError("Choose one SQLite path argument")
    application.state.store = Store(sqlite_path or db_path or os.environ.get("SQLITE_PATH") or default_path)
    application.include_router(router)

    @application.get("/api/health")
    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "campus-lab-escape"}

    @application.exception_handler(Exception)
    async def internal_error(request: Request, exception: Exception):
        # Never serialize exception details, credentials, or private state.
        return JSONResponse(error_body(new_id(), "INTERNAL_ERROR", "服务暂时无法完成请求。"), status_code=500)

    return application


app = create_app()
