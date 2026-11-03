from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.analysis import router as analysis_router
from app.api.decisions import router as decisions_router
from app.api.planning import router as planning_router
from app.api.simulations import router as simulations_router
from app.api.workspace import router as workspace_router
from app.settings import settings


def create_app() -> FastAPI:
    application = FastAPI(
        title="LaunchScope: Content & Games Measurement Design Lab",
        version="1.0.0",
        description="Educational measurement planning and fixed synthetic scenarios. Not Netflix methodology or outcomes.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-CSRF-Token"],
    )
    application.include_router(analysis_router)
    application.include_router(auth_router)
    application.include_router(planning_router)
    application.include_router(simulations_router)
    application.include_router(decisions_router)
    application.include_router(workspace_router)

    @application.get("/api/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "launchscope-api"}

    return application


app = create_app()