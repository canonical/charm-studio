from __future__ import annotations
from typing import Literal, Optional, Union
from pydantic import BaseModel, Field
import uuid

# ── Import sources ──────────────────────────────────────────────────────────

class GitSource(BaseModel):
    type: Literal["git"]
    url: str
    branch: Optional[str] = None
    credentials: Optional[str] = None  # optional PAT / password

class BitbucketSource(BaseModel):
    type: Literal["bitbucket"]
    workspace: str
    repo_slug: str
    branch: Optional[str] = None
    access_token: str

class UrlSource(BaseModel):
    type: Literal["url"]
    url: str  # .zip or .tar.gz

ImportSource = Union[GitSource, BitbucketSource, UrlSource]

# ── Request ──────────────────────────────────────────────────────────────────

class PipelineRequest(BaseModel):
    source: ImportSource = Field(..., discriminator="type")

# ── Stage status ─────────────────────────────────────────────────────────────

StageStatus = Literal["pending", "running", "done", "failed", "cancelled"]
StageName = Literal["verify", "12factor-charm", "12factor-rock", "deploy"]

class Stage(BaseModel):
    name: StageName
    status: StageStatus = "pending"
    started_at: Optional[str] = None   # ISO-8601
    finished_at: Optional[str] = None
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
    error: Optional[str] = None
    stages: list[Stage] = Field(default_factory=lambda: [
        Stage(name="verify"),
        Stage(name="12factor-charm"),
        Stage(name="12factor-rock"),
        Stage(name="deploy"),
    ])
    result: Optional[PipelineResult] = None

# ── Pipeline created response (POST /pipeline) ───────────────────────────────

class PipelineCreated(BaseModel):
    pipeline_id: str
