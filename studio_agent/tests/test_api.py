"""Tests for the FastAPI endpoints."""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from studio_agent.models import PipelineStatus


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def workspace(tmp_path):
    """A temporary workspace directory."""
    return str(tmp_path)


@pytest.fixture()
def client(workspace):
    """TestClient with workspace patched to tmp dir and Huey task mocked."""
    with (
        patch("studio_agent.main.get_workspace_base_dir", return_value=workspace),
        patch("studio_agent.main.run_pipeline"),  # don't actually enqueue
    ):
        from studio_agent.main import app

        yield TestClient(app)


def _write_status(workspace: str, pipeline_id: str, status: PipelineStatus) -> None:
    dir_ = os.path.join(workspace, pipeline_id)
    os.makedirs(dir_, exist_ok=True)
    with open(os.path.join(dir_, "pipeline_status.json"), "w") as f:
        f.write(status.model_dump_json())


# ── POST /pipeline ────────────────────────────────────────────────────────────


class TestPostPipeline:
    def test_git_source_returns_201(self, client):
        resp = client.post(
            "/pipeline", json={"source": {"type": "git", "url": "https://github.com/org/repo.git"}}
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "pipeline_id" in body
        assert len(body["pipeline_id"]) == 36  # UUID format

    def test_bitbucket_source_returns_201(self, client):
        resp = client.post(
            "/pipeline",
            json={
                "source": {
                    "type": "bitbucket",
                    "workspace": "myworkspace",
                    "repo_slug": "myrepo",
                    "access_token": "tok123",
                }
            },
        )
        assert resp.status_code == 201
        assert "pipeline_id" in resp.json()

    def test_url_source_returns_201(self, client):
        resp = client.post(
            "/pipeline", json={"source": {"type": "url", "url": "https://example.com/repo.tar.gz"}}
        )
        assert resp.status_code == 201

    def test_missing_source_returns_422(self, client):
        resp = client.post("/pipeline", json={})
        assert resp.status_code == 422

    def test_unknown_source_type_returns_422(self, client):
        resp = client.post(
            "/pipeline", json={"source": {"type": "ftp", "url": "ftp://example.com/repo"}}
        )
        assert resp.status_code == 422

    def test_git_source_missing_url_returns_422(self, client):
        resp = client.post("/pipeline", json={"source": {"type": "git"}})
        assert resp.status_code == 422


# ── GET /status/<pipeline_id> ─────────────────────────────────────────────────


class TestGetStatus:
    def test_existing_pipeline_returns_200(self, client, workspace):
        status = PipelineStatus(pipeline_id="abc-123")
        _write_status(workspace, "abc-123", status)
        resp = client.get("/status/abc-123")
        assert resp.status_code == 200
        body = resp.json()
        assert body["pipeline_id"] == "abc-123"
        assert body["done"] is False
        assert len(body["stages"]) == 4
        assert [s["name"] for s in body["stages"]] == [
            "verify",
            "12factor-charm",
            "12factor-rock",
            "deploy",
        ]

    def test_missing_pipeline_returns_404(self, client):
        resp = client.get("/status/does-not-exist")
        assert resp.status_code == 404

    def test_done_pipeline_includes_result(self, client, workspace):
        from studio_agent.models import PipelineResult, Stage

        status = PipelineStatus(
            pipeline_id="done-123",
            done=True,
            stages=[
                Stage(name="verify", status="done"),
                Stage(name="12factor-charm", status="done"),
                Stage(name="12factor-rock", status="done"),
                Stage(name="deploy", status="done"),
            ],
            result=PipelineResult(
                charm_file="/ws/done-123/my.charm",
                rock_file="/ws/done-123/my.rock",
                juju_model="done-123",
                juju_app="done-123",
            ),
        )
        _write_status(workspace, "done-123", status)
        resp = client.get("/status/done-123")
        assert resp.status_code == 200
        body = resp.json()
        assert body["done"] is True
        assert body["result"]["charm_file"] == "/ws/done-123/my.charm"

    def test_failed_pipeline_has_error(self, client, workspace):
        status = PipelineStatus(pipeline_id="fail-123", done=True, error="verify failed")
        _write_status(workspace, "fail-123", status)
        resp = client.get("/status/fail-123")
        assert resp.status_code == 200
        assert resp.json()["error"] == "verify failed"


# ── DELETE /pipeline/<pipeline_id> ───────────────────────────────────────────


class TestDeletePipeline:
    def test_cancel_running_pipeline_returns_204(self, client, workspace):
        status = PipelineStatus(pipeline_id="run-123", done=False)
        _write_status(workspace, "run-123", status)
        resp = client.delete("/pipeline/run-123")
        assert resp.status_code == 204
        # cancel flag file should exist
        assert os.path.exists(os.path.join(workspace, "run-123", ".cancel"))

    def test_cancel_done_pipeline_returns_409(self, client, workspace):
        status = PipelineStatus(pipeline_id="done-456", done=True)
        _write_status(workspace, "done-456", status)
        resp = client.delete("/pipeline/done-456")
        assert resp.status_code == 409
        assert "already completed" in resp.json()["detail"]

    def test_cancel_missing_pipeline_returns_404(self, client):
        resp = client.delete("/pipeline/not-found")
        assert resp.status_code == 404
