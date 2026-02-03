from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.logging import configure_logging

def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title="Tamil Government & Bank Message Explainer",
        version="1.0.0",
    )

    # 🔥 FORCE-ALLOW CORS (demo-safe)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,  # IMPORTANT with "*"
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    return app

app = create_app()
