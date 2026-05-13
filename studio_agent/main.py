from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from .config import get_workspace_base_dir
from .models import PipelineCreated, PipelineRequest, PipelineStatus
from .tasks import huey, load_status, request_cancel, run_pipeline  # noqa: F401

app = FastAPI(title="Charm Studio Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/pipeline", response_model=PipelineCreated, status_code=201)
def post_pipeline(body: PipelineRequest) -> PipelineCreated:
    pipeline_id = str(uuid.uuid4())
    run_pipeline(pipeline_id, body.source.model_dump())
    return PipelineCreated(pipeline_id=pipeline_id)


@app.get("/status/{pipeline_id}", response_model=PipelineStatus)
def get_status(pipeline_id: str) -> PipelineStatus:
    workspace_base_dir = get_workspace_base_dir()
    status = load_status(workspace_base_dir, pipeline_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return status


@app.delete("/pipeline/{pipeline_id}", status_code=204)
def delete_pipeline(pipeline_id: str) -> Response:
    workspace_base_dir = get_workspace_base_dir()
    status = load_status(workspace_base_dir, pipeline_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if status.done:
        raise HTTPException(status_code=409, detail="Pipeline already completed.")
    request_cancel(workspace_base_dir, pipeline_id)
    return Response(status_code=204)
