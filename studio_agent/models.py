from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ── Import source ───────────────────────────────────────────────────────────


class GitSource(BaseModel):
    url: str
    branch: str | None = None
    credentials: str | None = None  # optional PAT / password


# ── Request ──────────────────────────────────────────────────────────────────


class PipelineRequest(BaseModel):
    source: GitSource


# ── Stage status ─────────────────────────────────────────────────────────────

StageStatus = Literal["pending", "running", "done", "failed", "cancelled"]
StageName = Literal["verify", "12factor-charm", "12factor-rock", "deploy"]


class Stage(BaseModel):
    name: StageName
    status: StageStatus = "pending"
    started_at: str | None = None  # ISO-8601
    finished_at: str | None = None
    stdout: str = ""
    stderr: str = ""


# ── Pipeline result ──────────────────────────────────────────────────────────


class PipelineResult(BaseModel):
    charm_file: str
    rock_file: str
    juju_model: str
    juju_app: str


# ── Pipeline status (GET /status response) ───────────────────────────────────


class PipelineStatus(BaseModel):
    pipeline_id: str
    done: bool = False
    error: str | None = None
    stages: list[Stage] = Field(
        default_factory=lambda: [
            Stage(name="verify"),
            Stage(name="12factor-charm"),
            Stage(name="12factor-rock"),
            Stage(name="deploy"),
        ]
    )
    result: PipelineResult | None = None


# ── Pipeline created response (POST /pipeline) ───────────────────────────────


class PipelineCreated(BaseModel):
    pipeline_id: str
