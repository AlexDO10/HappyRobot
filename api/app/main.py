from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes import router
from app.stores import calls_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    calls_store.init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="HappyRobot — Inbound Carrier Sales API",
        version="1.0.0",
        description=(
            "Backend tools for a HappyRobot voice agent: load search, FMCSA "
            "carrier verification, deterministic offer evaluation, and call analytics."
        ),
        lifespan=lifespan,
    )

    # Allow the (separate) dashboard frontend to call the API from a browser.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Unauthenticated health check for the managed host's uptime probe.
    @app.get("/health", tags=["meta"])
    def health():
        return {"status": "ok", "fmcsa_mode": "mock" if settings.fmcsa_is_mock else "live"}

    app.include_router(router)
    return app


app = create_app()
