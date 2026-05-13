"""Unit tests for the /pipeline, /status, and DELETE /pipeline endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from studio_agent.main import app
from studio_agent.models import PipelineResult, PipelineStatus, Stage

client = TestClient(app)

# ── helpers ──────────────────────────────────────────────────────────────────

GIT_BODY = {"source": {"type": "git", "url": "https://github.com/example/repo"}}
BITBUCKET_BODY = {
    "source": {
        "type": "bitbucket",
        "workspace": "my-org",
        "repo_slug": "my-repo",
        "access_token": "tok",
    }
}
URL_BODY = {"source": {"type": "url", "url": "https://example.com/repo.tar.gz"}}


def _running_status(pipeline_id: str = "test-id") -> PipelineStatus:
    stages = [
        Stage(name="verify", status="done"),
        Stage(name="12factor-charm", status="running"),
        Stage(name="12factor-rock", status="running"),
        Stage(name="deploy", status="pending"),
    ]
    return PipelineStatus(pipeline_id=pipeline_id, done=False, stages=stages)


def _done_status(pipeline_id: str = "test-id") -> PipelineStatus:
    stages = [
        Stage(name=n, status="done")
        for n in ("verify", "12factor-charm", "12factor-rock", "deploy")
    ]  # type: ignore[arg-type]
    return PipelineStatus(
        pipeline_id=pipeline_id,
        done=True,
        stages=stages,
        result=PipelineResult(
            charm_file="/ws/test-id/my.charm",
            rock_file="/ws/test-id/my.rock",
            juju_model="test-id",
            juju_app="test-id",
        ),
    )


# ── POST /pipeline ────────────────────────────────────────────────────────────


class TestPostPipeline:
    @patch("studio_agent.main.uuid.uuid4", return_value="mocked-pipeline-id")
    @patch("studio_agent.main.run_pipeline")
    def test_pipeline_id_uses_mocked_uuid(self, mock_run: MagicMock, _mock_uuid: MagicMock) -> None:
        resp = client.post("/pipeline", json=GIT_BODY)
        assert resp.status_code == 201
        assert resp.json()["pipeline_id"] == "mocked-pipeline-id"
        mock_run.assert_called_once_with(
            "mocked-pipeline-id",
            {
                "type": "git",
                "url": "https://github.com/example/repo",
                "branch": None,
                "credentials": None,
            },
        )

    @patch("studio_agent.main.run_pipeline")
    def test_git_source_returns_201(self, mock_run: MagicMock) -> None:
        resp = client.post("/pipeline", json=GIT_BODY)
        assert resp.status_code == 201

    @patch("studio_agent.main.run_pipeline")
    def test_git_source_returns_pipeline_id(self, mock_run: MagicMock) -> None:
        resp = client.post("/pipeline", json=GIT_BODY)
        data = resp.json()
        assert "pipeline_id" in data
        assert len(data["pipeline_id"]) == 36  # UUID4 string length

    @patch("studio_agent.main.run_pipeline")
    def test_each_request_gets_unique_pipeline_id(self, mock_run: MagicMock) -> None:
        ids = {client.post("/pipeline", json=GIT_BODY).json()["pipeline_id"] for _ in range(3)}
        assert len(ids) == 3

    @patch("studio_agent.main.run_pipeline")
    def test_run_pipeline_task_is_enqueued(self, mock_run: MagicMock) -> None:
        resp = client.post("/pipeline", json=GIT_BODY)
        pipeline_id = resp.json()["pipeline_id"]
        mock_run.assert_called_once_with(
            pipeline_id,
            {
                "type": "git",
                "url": "https://github.com/example/repo",
                "branch": None,
                "credentials": None,
            },
        )

    @patch("studio_agent.main.run_pipeline")
    def test_bitbucket_source_returns_201(self, mock_run: MagicMock) -> None:
        resp = client.post("/pipeline", json=BITBUCKET_BODY)
        assert resp.status_code == 201
        pipeline_id = resp.json()["pipeline_id"]
        mock_run.assert_called_once_with(
            pipeline_id,
            {
                "type": "bitbucket",
                "workspace": "my-org",
                "repo_slug": "my-repo",
                "branch": None,
                "access_token": "tok",
            },
        )

    @patch("studio_agent.main.run_pipeline")
    def test_url_source_returns_201(self, mock_run: MagicMock) -> None:
        resp = client.post("/pipeline", json=URL_BODY)
        assert resp.status_code == 201
        pipeline_id = resp.json()["pipeline_id"]
        mock_run.assert_called_once_with(
            pipeline_id,
            {"type": "url", "url": "https://example.com/repo.tar.gz"},
        )

    @patch("studio_agent.main.run_pipeline")
    def test_git_source_with_branch(self, mock_run: MagicMock) -> None:
        body = {"source": {"type": "git", "url": "https://github.com/x/y", "branch": "main"}}
        resp = client.post("/pipeline", json=body)
        assert resp.status_code == 201
        _, kwargs_source = mock_run.call_args[0]
        assert kwargs_source["branch"] == "main"

    def test_missing_body_returns_422(self) -> None:
        resp = client.post("/pipeline", json={})
        assert resp.status_code == 422

    def test_unknown_source_type_returns_422(self) -> None:
        resp = client.post("/pipeline", json={"source": {"type": "ftp", "url": "ftp://x"}})
        assert resp.status_code == 422

    def test_git_source_missing_url_returns_422(self) -> None:
        resp = client.post("/pipeline", json={"source": {"type": "git"}})
        assert resp.status_code == 422

    def test_bitbucket_missing_access_token_returns_422(self) -> None:
        resp = client.post(
            "/pipeline",
            json={"source": {"type": "bitbucket", "workspace": "org", "repo_slug": "r"}},
        )
        assert resp.status_code == 422


# ── GET /status ───────────────────────────────────────────────────────────────


class TestGetStatus:
    @patch("studio_agent.main.get_workspace_base_dir", return_value="/ws")
    @patch("studio_agent.main.load_status")
    def test_returns_200_when_found(self, mock_load: MagicMock, _mock_dir: MagicMock) -> None:
        mock_load.return_value = _running_status()
        resp = client.get("/status/test-id")
        assert resp.status_code == 200

    @patch("studio_agent.main.get_workspace_base_dir", return_value="/ws")
    @patch("studio_agent.main.load_status")
    def test_returns_pipeline_id(self, mock_load: MagicMock, _mock_dir: MagicMock) -> None:
        mock_load.return_value = _running_status("abc-123")
        resp = client.get("/status/abc-123")
        assert resp.json()["pipeline_id"] == "abc-123"

    @patch("studio_agent.main.get_workspace_base_dir", return_value="/ws")
    @patch("studio_agent.main.load_status")
    def test_running_pipeline_done_is_false(
        self, mock_load: MagicMock, _mock_dir: MagicMock
    ) -> None:
        mock_load.return_value = _running_status()
        assert client.get("/status/test-id").json()["done"] is False

    @patch("studio_agent.main.get_workspace_base_dir", return_value="/ws")
    @patch("studio_agent.main.load_status")
    def test_done_pipeline_has_result(self, mock_load: MagicMock, _mock_dir: MagicMock) -> None:
        mock_load.return_value = _done_status()
        data = client.get("/status/test-id").json()
        assert data["done"] is True
        assert data["result"]["charm_file"] == "/ws/test-id/my.charm"
        assert data["result"]["rock_file"] == "/ws/test-id/my.rock"

    @patch("studio_agent.main.get_workspace_base_dir", return_value="/ws")
    @patch("studio_agent.main.load_status")
    def test_stages_array_has_four_entries(
        self, mock_load: MagicMock, _mock_dir: MagicMock
    ) -> None:
        mock_load.return_value = _running_status()
        stages = client.get("/status/test-id").json()["stages"]
        assert len(stages) == 4
        assert [s["name"] for s in stages] == [
            "verify",
            "12factor-charm",
            "12factor-rock",
            "deploy",
        ]

    @patch("studio_agent.main.get_workspace_base_dir", return_value="/ws")
    @patch("studio_agent.main.load_status", return_value=None)
    def test_not_found_returns_404(self, _mock_load: MagicMock, _mock_dir: MagicMock) -> None:
        resp = client.get("/status/no-such-id")
        assert resp.status_code == 404

    @patch("studio_agent.main.get_workspace_base_dir", return_value="/ws")
    @patch("studio_agent.main.load_status")
    def test_load_status_called_with_correct_args(
        self, mock_load: MagicMock, _mock_dir: MagicMock
    ) -> None:
        mock_load.return_value = _running_status("my-pipe")
        client.get("/status/my-pipe")
        mock_load.assert_called_once_with("/ws", "my-pipe")


# ── DELETE /pipeline ──────────────────────────────────────────────────────────


class TestDeletePipeline:
    @patch("studio_agent.main.get_workspace_base_dir", return_value="/ws")
    @patch("studio_agent.main.request_cancel")
    @patch("studio_agent.main.load_status")
    def test_cancel_running_pipeline_returns_204(
        self, mock_load: MagicMock, mock_cancel: MagicMock, _mock_dir: MagicMock
    ) -> None:
        mock_load.return_value = _running_status()
        resp = client.delete("/pipeline/test-id")
        assert resp.status_code == 204

    @patch("studio_agent.main.get_workspace_base_dir", return_value="/ws")
    @patch("studio_agent.main.request_cancel")
    @patch("studio_agent.main.load_status")
    def test_cancel_calls_request_cancel(
        self, mock_load: MagicMock, mock_cancel: MagicMock, _mock_dir: MagicMock
    ) -> None:
        mock_load.return_value = _running_status("run-1")
        client.delete("/pipeline/run-1")
        mock_cancel.assert_called_once_with("/ws", "run-1")

    @patch("studio_agent.main.get_workspace_base_dir", return_value="/ws")
    @patch("studio_agent.main.load_status", return_value=None)
    def test_delete_not_found_returns_404(
        self, _mock_load: MagicMock, _mock_dir: MagicMock
    ) -> None:
        resp = client.delete("/pipeline/ghost-id")
        assert resp.status_code == 404

    @patch("studio_agent.main.get_workspace_base_dir", return_value="/ws")
    @patch("studio_agent.main.load_status")
    def test_delete_completed_pipeline_returns_409(
        self, mock_load: MagicMock, _mock_dir: MagicMock
    ) -> None:
        mock_load.return_value = _done_status()
        resp = client.delete("/pipeline/done-id")
        assert resp.status_code == 409
