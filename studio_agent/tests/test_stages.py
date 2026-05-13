"""Tests for stage runner functions."""
from __future__ import annotations

import os
import threading
from unittest.mock import MagicMock, call, patch

import pytest

from studio_agent.models import PipelineStatus, Stage


def _cancel() -> threading.Event:
    return threading.Event()


def _cancelled() -> threading.Event:
    e = threading.Event()
    e.set()
    return e


def _make_proc(returncode: int = 0, stdout: str = "ok", stderr: str = "") -> MagicMock:
    """Return a mock subprocess.Popen-compatible object."""
    proc = MagicMock()
    proc.communicate.return_value = (stdout, stderr)
    proc.returncode = returncode
    return proc


# ── _run_cmd (via run_verify as proxy) ───────────────────────────────────────

class TestRunCmd:
    def test_success_marks_stage_done(self, tmp_path):
        status = PipelineStatus(pipeline_id="p1")
        stage = next(s for s in status.stages if s.name == "verify")
        stage.status = "running"

        with patch("subprocess.Popen", return_value=_make_proc(0, "stdout text", "")) as mock_popen:
            from studio_agent.stages import _run_cmd
            ok = _run_cmd(["echo", "hi"], str(tmp_path), stage, _cancel())

        assert ok is True
        assert stage.status == "done"
        assert stage.stdout == "stdout text"
        assert stage.started_at is not None
        assert stage.finished_at is not None

    def test_nonzero_exit_marks_stage_failed(self, tmp_path):
        status = PipelineStatus(pipeline_id="p2")
        stage = next(s for s in status.stages if s.name == "verify")
        stage.status = "running"

        with patch("subprocess.Popen", return_value=_make_proc(1, "", "oops")):
            from studio_agent.stages import _run_cmd
            ok = _run_cmd(["false"], str(tmp_path), stage, _cancel())

        assert ok is False
        assert stage.status == "failed"
        assert stage.stderr == "oops"

    def test_cancel_event_marks_stage_cancelled(self, tmp_path):
        stage = Stage(name="verify", status="running")

        proc = MagicMock()
        proc.communicate.side_effect = [
            __import__("subprocess").TimeoutExpired("cmd", 2),
        ]

        cancel = threading.Event()
        cancel.set()

        with patch("subprocess.Popen", return_value=proc):
            from studio_agent.stages import _run_cmd
            ok = _run_cmd(["sleep", "9999"], str(tmp_path), stage, cancel)

        assert ok is False
        assert stage.status == "cancelled"


# ── run_verify ────────────────────────────────────────────────────────────────

class TestRunVerify:
    def test_success(self, tmp_path):
        status = PipelineStatus(pipeline_id="v1")
        with patch("subprocess.Popen", return_value=_make_proc(0, "verified", "")):
            from studio_agent.stages import run_verify
            ok = run_verify(str(tmp_path), status, _cancel())
        assert ok is True
        stage = next(s for s in status.stages if s.name == "verify")
        assert stage.status == "done"

    def test_failure(self, tmp_path):
        status = PipelineStatus(pipeline_id="v2")
        with patch("subprocess.Popen", return_value=_make_proc(1, "", "bad repo")):
            from studio_agent.stages import run_verify
            ok = run_verify(str(tmp_path), status, _cancel())
        assert ok is False
        stage = next(s for s in status.stages if s.name == "verify")
        assert stage.status == "failed"
        assert "bad repo" in stage.stderr


# ── run_12factor_charm / run_12factor_rock ────────────────────────────────────

class TestRun12Factor:
    def test_charm_success(self, tmp_path):
        status = PipelineStatus(pipeline_id="c1")
        with patch("subprocess.Popen", return_value=_make_proc(0)):
            from studio_agent.stages import run_12factor_charm
            ok = run_12factor_charm(str(tmp_path), status, _cancel())
        assert ok is True
        stage = next(s for s in status.stages if s.name == "12factor-charm")
        assert stage.status == "done"

    def test_rock_success(self, tmp_path):
        status = PipelineStatus(pipeline_id="r1")
        with patch("subprocess.Popen", return_value=_make_proc(0)):
            from studio_agent.stages import run_12factor_rock
            ok = run_12factor_rock(str(tmp_path), status, _cancel())
        assert ok is True
        stage = next(s for s in status.stages if s.name == "12factor-rock")
        assert stage.status == "done"

    def test_charm_failure(self, tmp_path):
        status = PipelineStatus(pipeline_id="c2")
        with patch("subprocess.Popen", return_value=_make_proc(1, "", "charm err")):
            from studio_agent.stages import run_12factor_charm
            ok = run_12factor_charm(str(tmp_path), status, _cancel())
        assert ok is False


# ── run_deploy ────────────────────────────────────────────────────────────────

class TestRunDeploy:
    def _setup_project(self, tmp_path) -> str:
        project = tmp_path / "myproject"
        project.mkdir()
        (project / "my.charm").write_text("")
        (project / "my.rock").write_text("")
        return str(project)

    def test_success_sets_result(self, tmp_path):
        project = self._setup_project(tmp_path)
        status = PipelineStatus(pipeline_id="d1")

        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="ok\n", stderr="")):
            from studio_agent.stages import run_deploy
            ok = run_deploy(project, status, _cancel(), "d1", "admin/haproxy:http")

        assert ok is True
        assert status.result is not None
        assert status.result.juju_model == "d1"
        assert status.result.juju_app == "d1"
        assert status.result.charm_file.endswith("my.charm")
        assert status.result.rock_file.endswith("my.rock")

    def test_missing_charm_file_fails(self, tmp_path):
        project = tmp_path / "empty"
        project.mkdir()
        status = PipelineStatus(pipeline_id="d2")

        from studio_agent.stages import run_deploy
        ok = run_deploy(str(project), status, _cancel(), "d2", "admin/haproxy:http")

        assert ok is False
        stage = next(s for s in status.stages if s.name == "deploy")
        assert stage.status == "failed"
        assert "Expected one .charm" in stage.stderr

    def test_juju_command_failure_marks_failed(self, tmp_path):
        project = self._setup_project(tmp_path)
        status = PipelineStatus(pipeline_id="d3")

        with patch("subprocess.run", return_value=MagicMock(returncode=1, stdout="", stderr="juju error")):
            from studio_agent.stages import run_deploy
            ok = run_deploy(str(project), status, _cancel(), "d3", "admin/haproxy:http")

        assert ok is False
        stage = next(s for s in status.stages if s.name == "deploy")
        assert stage.status == "failed"


# ── run_clone ─────────────────────────────────────────────────────────────────

class TestRunClone:
    def test_git_clone_success(self, tmp_path):
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            from studio_agent.stages import run_clone
            ok, path = run_clone(
                {"type": "git", "url": "https://github.com/org/repo.git"},
                str(tmp_path), "my-project", _cancel(),
            )
        assert ok is True
        assert path == str(tmp_path / "my-project")

    def test_git_clone_failure(self, tmp_path):
        with patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="auth failed")):
            from studio_agent.stages import run_clone
            ok, msg = run_clone(
                {"type": "git", "url": "https://github.com/org/repo.git"},
                str(tmp_path), "my-project", _cancel(),
            )
        assert ok is False
        assert "auth failed" in msg

    def test_git_clone_with_branch(self, tmp_path):
        with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            from studio_agent.stages import run_clone
            run_clone(
                {"type": "git", "url": "https://github.com/org/repo.git", "branch": "dev"},
                str(tmp_path), "proj", _cancel(),
            )
        cmd = mock_run.call_args[0][0]
        assert "--branch" in cmd
        assert "dev" in cmd

    def test_unknown_type_fails(self, tmp_path):
        from studio_agent.stages import run_clone
        ok, msg = run_clone({"type": "ftp"}, str(tmp_path), "proj", _cancel())
        assert ok is False
        assert "Unknown source type" in msg


# ── tasks helpers ─────────────────────────────────────────────────────────────

class TestTasksHelpers:
    def test_save_and_load_status(self, tmp_path):
        from studio_agent.tasks import load_status, save_status
        status = PipelineStatus(pipeline_id="t1")
        save_status(str(tmp_path), "t1", status)
        loaded = load_status(str(tmp_path), "t1")
        assert loaded is not None
        assert loaded.pipeline_id == "t1"
        assert len(loaded.stages) == 4

    def test_load_missing_returns_none(self, tmp_path):
        from studio_agent.tasks import load_status
        assert load_status(str(tmp_path), "no-such-id") is None

    def test_request_and_is_cancel(self, tmp_path):
        from studio_agent.tasks import is_cancel_requested, request_cancel
        pid = "cancel-test"
        os.makedirs(os.path.join(str(tmp_path), pid))
        assert not is_cancel_requested(str(tmp_path), pid)
        request_cancel(str(tmp_path), pid)
        assert is_cancel_requested(str(tmp_path), pid)
