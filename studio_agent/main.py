from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_workspace_base_dir
from .log import configure_logging
from .models import DeployRequest, PipelineCreated, PipelineRequest, PipelineStatus
from .tasks import huey, load_status, request_cancel, run_deploy_only, run_pipeline  # noqa: F401

configure_logging()
logger = logging.getLogger(__name__)

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
    logger.info("Pipeline %s created (source: %s)", pipeline_id, body.source.model_dump())
    run_pipeline(pipeline_id, body.source.model_dump())
    return PipelineCreated(pipeline_id=pipeline_id)


@app.get("/status/{pipeline_id}", response_model=PipelineStatus)
def get_status(pipeline_id: str) -> PipelineStatus:
    workspace_base_dir = get_workspace_base_dir()
    status = load_status(workspace_base_dir, pipeline_id)
    if status is None:
        logger.warning("Status requested for unknown pipeline %s", pipeline_id)
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return status


@app.post("/deploy", response_model=PipelineCreated, status_code=202)
def post_deploy(body: DeployRequest) -> PipelineCreated:
    """Trigger the deploy stage only for an existing pipeline workspace.

    The workspace must already contain a packed .charm and .rock file.
    Use GET /status/{pipeline_id} to track progress.
    """
    logger.info("Deploy-only requested for pipeline %s", body.pipeline_id)
    run_deploy_only(body.pipeline_id)
    return PipelineCreated(pipeline_id=body.pipeline_id)


@app.delete("/pipeline/{pipeline_id}", status_code=204)
def delete_pipeline(pipeline_id: str) -> Response:
    workspace_base_dir = get_workspace_base_dir()
    status = load_status(workspace_base_dir, pipeline_id)
    if status is None:
        logger.warning("Cancel requested for unknown pipeline %s", pipeline_id)
        raise HTTPException(status_code=404, detail="Pipeline not found")
    if status.done:
        logger.warning("Cancel requested for already-completed pipeline %s", pipeline_id)
        raise HTTPException(status_code=409, detail="Pipeline already completed.")
    logger.info("Cancel requested for pipeline %s", pipeline_id)
    request_cancel(workspace_base_dir, pipeline_id)
    return Response(status_code=204)


# Serve the React frontend from $SNAP/static (or ./frontend/dist for dev)
_snap_dir = os.environ.get("SNAP", "")
_static_dir = (
    Path(_snap_dir) / "static" if _snap_dir else Path(__file__).parent.parent / "frontend" / "dist"
)

if _static_dir.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_static_dir / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str) -> FileResponse:
        return FileResponse(str(_static_dir / "index.html"))
