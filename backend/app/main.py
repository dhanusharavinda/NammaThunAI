from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="Tamil Government & Bank Message Explainer",
        version="1.0.0",
    )

    # Be tolerant in local dev: browsers may use localhost while API points to 127.0.0.1.
    allowed_origins = {
        (settings.frontend_origin or "").rstrip("/"),
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    }
    allowed_origins.discard("")



    app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all for demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router)
    return app


app = create_app()

