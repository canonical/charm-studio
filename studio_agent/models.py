from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# ── Import sources ──────────────────────────────────────────────────────────


class GitSource(BaseModel):
    type: Literal["git"]
    url: str
    branch: str | None = None
    credentials: str | None = None  # optional PAT / password


class BitbucketSource(BaseModel):
    type: Literal["bitbucket"]
    workspace: str
    repo_slug: str
    branch: str | None = None
    access_token: str


class UrlSource(BaseModel):
    type: Literal["url"]
    url: str  # .zip or .tar.gz


ImportSource = GitSource | BitbucketSource | UrlSource

# ── Request ──────────────────────────────────────────────────────────────────


class PipelineRequest(BaseModel):
    source: ImportSource = Field(..., discriminator="type")


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
