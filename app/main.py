from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.models import (
    AssistantBootstrapResponse,
    ChatRequest,
    ChatResponse,
    ValidateFieldRequest,
    ValidateFieldResponse,
)
from app.services.chat import build_bootstrap_response, build_chat_response
from app.services.template_service import get_template_schema
from app.services.validation import validate_field_value


BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(title="Template Assistant", version="0.1.0")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/api/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.get("/api/template/{template_id}/schema")
def template_schema(template_id: str) -> dict:
    schema = get_template_schema(template_id)
    if schema is None:
        raise HTTPException(status_code=404, detail="Template not found.")

    return schema.model_dump()


@app.post("/api/validate/field", response_model=ValidateFieldResponse)
def validate_field(payload: ValidateFieldRequest) -> ValidateFieldResponse:
    return validate_field_value(payload)


@app.post("/api/chat/message", response_model=ChatResponse)
def chat_message(payload: ChatRequest) -> ChatResponse:
    return build_chat_response(payload)


@app.get("/api/assistant/bootstrap", response_model=AssistantBootstrapResponse)
def assistant_bootstrap() -> AssistantBootstrapResponse:
    return build_bootstrap_response()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/{asset_path:path}")
def assets(asset_path: str):
    asset = WEB_DIR / asset_path
    if asset.is_file():
        return FileResponse(asset)
    raise HTTPException(status_code=404, detail="File not found.")
