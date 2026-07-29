"""FastAPI application entrypoint."""

import warnings

# 须在 import requests 之前；根因见 pyproject chardet<6 与 pip install -e 重装
warnings.filterwarnings(
    "ignore",
    message=r"urllib3 .* or chardet .* doesn't match a supported version",
)

from contextlib import asynccontextmanager

from aperix_geo.utils.logging import configure

configure()

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response

from aperix_geo.api.routes import analysis, auth, billing, competitors, diagnosis, notifications, opportunity
from aperix_geo.api.routes import favicon as favicon_routes
from aperix_geo.api.routes import ops_doubao, prompts, reports, responses, sampling, subjects, topics
from aperix_geo.services.favicon import ensure_storage_dir


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_storage_dir()
    yield


app = FastAPI(title="Aperix AI API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """浏览器打开根路径时进入 Swagger UI。"""
    return RedirectResponse(url="/docs")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """避免浏览器自动请求产生无意义 404 日志。"""
    return Response(status_code=204)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(auth.router)
api_v1.include_router(billing.router)
api_v1.include_router(notifications.router)
api_v1.include_router(subjects.router)
api_v1.include_router(competitors.router)
api_v1.include_router(topics.router)
api_v1.include_router(prompts.router)
api_v1.include_router(sampling.router)
api_v1.include_router(responses.router)
api_v1.include_router(analysis.router)
api_v1.include_router(diagnosis.router)
api_v1.include_router(opportunity.router)
api_v1.include_router(reports.router)
api_v1.include_router(favicon_routes.router)
api_v1.include_router(ops_doubao.router)

app.include_router(api_v1)
