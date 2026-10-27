import secrets
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app import models  # noqa: F401
from app.routers import auth, games, goals, insights, integrations, sessions


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.environment == "development":
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", description="API pessoal para biblioteca e atividade de jogos",
              lifespan=lifespan)


@app.middleware("http")
async def csrf_guard(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path.startswith("/api/"):
        origin = request.headers.get("origin")
        if origin and origin not in settings.cors_origin_list:
            return JSONResponse(status_code=403, content={"detail": "Origem não permitida"})
        if request.cookies.get("gametracker_session"):
            cookie_token = request.cookies.get("gametracker_csrf", "")
            header_token = request.headers.get("x-csrf-token", "")
            if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
                return JSONResponse(status_code=403, content={"detail": "Validação CSRF inválida"})
    return await call_next(request)


app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True,
                   allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
                   allow_headers=["Content-Type", "X-CSRF-Token"])

api = APIRouter(prefix="/api")
api.include_router(auth.router)
api.include_router(games.router)
api.include_router(sessions.router)
api.include_router(goals.router)
api.include_router(insights.router)
api.include_router(integrations.router)
app.include_router(api)


@app.get("/health")
def health():
    return {"status": "ok"}
