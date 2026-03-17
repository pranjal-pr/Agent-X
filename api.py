from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from crew_service import analyze_stock
from models import AnalyzeRequest, AnalyzeResponse, AttachmentSummary

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
MAX_ATTACHMENTS = 6
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024

app = FastAPI(
    title="Groq Multi-Agent Stock Analysis Syndicate",
    version="1.0.0",
    description="A low-latency CrewAI stock analysis demo powered by Groq.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


async def _extract_attachments(form: Any) -> list[AttachmentSummary]:
    uploads = [
        value
        for key, value in form.multi_items()
        if key == "attachments" and getattr(value, "filename", None)
    ]
    if len(uploads) > MAX_ATTACHMENTS:
        raise ValueError(f"Attach up to {MAX_ATTACHMENTS} files or photos per request.")

    attachments: list[AttachmentSummary] = []
    for upload in uploads:
        payload = await upload.read(MAX_ATTACHMENT_BYTES + 1)
        size_bytes = len(payload)
        await upload.close()
        if size_bytes > MAX_ATTACHMENT_BYTES:
            raise ValueError(
                f"Attachment '{upload.filename}' exceeds the {MAX_ATTACHMENT_BYTES // (1024 * 1024)} MB limit."
            )

        media_type = (upload.content_type or "application/octet-stream").strip()
        attachments.append(
            AttachmentSummary(
                filename=upload.filename,
                media_type=media_type,
                size_bytes=size_bytes,
                kind="photo" if media_type.startswith("image/") else "file",
            )
        )

    return attachments


async def _parse_analyze_request(request: Request) -> tuple[AnalyzeRequest, list[AttachmentSummary]]:
    content_type = request.headers.get("content-type", "").lower()
    if content_type.startswith("application/json"):
        payload = AnalyzeRequest.model_validate(await request.json())
        return payload, []

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        payload = AnalyzeRequest(ticker=str(form.get("ticker", "")))
        attachments = await _extract_attachments(form)
        return payload, attachments

    raise ValueError("Unsupported request type. Use JSON or multipart form data.")


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: Request) -> AnalyzeResponse:
    try:
        payload, attachments = await _parse_analyze_request(request)
        return await analyze_stock(payload.ticker, attachments=attachments)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc
