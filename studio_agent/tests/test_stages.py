"""Tests for stage runner functions."""

from __future__ import annotations

import os
import threading
from unittest.mock import MagicMock, patch

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
    proc.__enter__ = MagicMock(return_value=proc)
    proc.__exit__ = MagicMock(return_value=False)
    return proc


# ── _run_cmd (via run_verify as proxy) ───────────────────────────────────────


class TestRunCmd:
    def test_success_marks_stage_done(self, tmp_path):
        status = PipelineStatus(pipeline_id="p1")
        stage = next(s for s in status.stages if s.name == "verify")
        stage.status = "running"

        with patch("subprocess.Popen", return_value=_make_proc(0, "stdout text", "")):
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

    def test_charm_pack_success(self, tmp_path):
        status = PipelineStatus(pipeline_id="cp1")
        with patch("subprocess.Popen", return_value=_make_proc(0)):
            from studio_agent.stages import run_charm_pack

            ok = run_charm_pack(str(tmp_path), status, _cancel())
        assert ok is True
        stage = next(s for s in status.stages if s.name == "12factor-charm")
        assert stage.status == "done"
        assert "charmcraft pack" in stage.stdout

    def test_rock_pack_success(self, tmp_path):
        status = PipelineStatus(pipeline_id="rp1")
        with patch("subprocess.Popen", return_value=_make_proc(0)):
            from studio_agent.stages import run_rock_pack

            ok = run_rock_pack(str(tmp_path), status, _cancel())
        assert ok is True
        stage = next(s for s in status.stages if s.name == "12factor-rock")
        assert stage.status == "done"
        assert "rockcraft pack" in stage.stdout


# ── run_deploy ────────────────────────────────────────────────────────────────


class TestRunDeploy:
    def _setup_project(
        self,
        tmp_path,
        charm_name="my",
        rock_name="my",
        charmcraft_yaml: str | None = None,
        charm_in_subdir: bool = False,
    ) -> str:
        project = tmp_path / "myproject"
        project.mkdir()
        charm_dir = project / "charm" if charm_in_subdir else project
        if charm_in_subdir:
            charm_dir.mkdir()
        (charm_dir / f"{charm_name}.charm").write_text("")
        (project / f"{rock_name}.rock").write_text("")
        if charmcraft_yaml:
            (project / "charmcraft.yaml").write_text(charmcraft_yaml)
        return str(project)

    def test_success_sets_result(self, tmp_path):
        project = self._setup_project(
            tmp_path, charm_name="spring-petclinic_amd64", rock_name="spring-petclinic_0.1_amd64"
        )
        status = PipelineStatus(pipeline_id="d1")

        with patch("subprocess.Popen", return_value=_make_proc(returncode=0)):
            from studio_agent.stages import run_deploy

            ok = run_deploy(project, status, _cancel(), "d1", "admin/haproxy:http")

        assert ok is True
        assert status.result is not None
        assert status.result.juju_model == "d1"
        assert status.result.juju_app == "spring-petclinic"
        assert status.result.charm_file.endswith("spring-petclinic_amd64.charm")
        assert status.result.rock_file.endswith("spring-petclinic_0.1_amd64.rock")

    def test_charm_in_charm_subdir(self, tmp_path):
        project = self._setup_project(
            tmp_path,
            charm_name="spring-petclinic_amd64",
            rock_name="spring-petclinic_0.1_amd64",
            charm_in_subdir=True,
        )
        status = PipelineStatus(pipeline_id="d1s")

        with patch("subprocess.Popen", return_value=_make_proc(returncode=0)):
            from studio_agent.stages import run_deploy

            ok = run_deploy(project, status, _cancel(), "d1s", "admin/haproxy:http")

        assert ok is True
        assert status.result.charm_file.endswith("spring-petclinic_amd64.charm")
        assert "charm/" in status.result.charm_file or "charm\\" in status.result.charm_file

    def test_resource_name_read_from_charmcraft_yaml(self, tmp_path):
        charmcraft_yaml = "extensions:\n  - flask-framework\n"
        project = self._setup_project(
            tmp_path,
            charm_name="myapp_amd64",
            rock_name="myapp_0.1_amd64",
            charmcraft_yaml=charmcraft_yaml,
        )
        status = PipelineStatus(pipeline_id="d1y")
        calls = []

        def _fake_popen(cmd, **kwargs):
            calls.append(cmd)
            return _make_proc(returncode=0)

        with patch("subprocess.Popen", side_effect=_fake_popen):
            from studio_agent.stages import run_deploy

            ok = run_deploy(project, status, _cancel(), "d1y", "admin/haproxy:http")

        assert ok is True
        juju_cmd = next(c for c in calls if c[0] == "juju" and c[1] == "deploy" and "--resource" in c)
        assert "--model" in juju_cmd
        assert "flask-app-image=localhost:32000/myapp:0.1" in " ".join(juju_cmd)

    def test_resource_name_go_framework_uses_app_image(self, tmp_path):
        charmcraft_yaml = "extensions:\n  - go-framework\n"
        project = self._setup_project(
            tmp_path,
            charm_name="myapp_amd64",
            rock_name="myapp_0.1_amd64",
            charmcraft_yaml=charmcraft_yaml,
        )
        status = PipelineStatus(pipeline_id="d1g")
        calls = []

        def _fake_popen(cmd, **kwargs):
            calls.append(cmd)
            return _make_proc(returncode=0)

        with patch("subprocess.Popen", side_effect=_fake_popen):
            from studio_agent.stages import run_deploy

            ok = run_deploy(project, status, _cancel(), "d1g", "admin/haproxy:http")

        assert ok is True
        juju_cmd = next(c for c in calls if c[0] == "juju" and c[1] == "deploy" and "--resource" in c)
        assert "app-image=localhost:32000/myapp:0.1" in " ".join(juju_cmd)

    def test_resource_name_falls_back_to_app_image(self, tmp_path):
        project = self._setup_project(
            tmp_path, charm_name="myapp_amd64", rock_name="myapp_0.2_amd64"
        )
        status = PipelineStatus(pipeline_id="d1r")
        calls = []

        def _fake_popen(cmd, **kwargs):
            calls.append(cmd)
            return _make_proc(returncode=0)

        with patch("subprocess.Popen", side_effect=_fake_popen):
            from studio_agent.stages import run_deploy

            ok = run_deploy(project, status, _cancel(), "d1r", "admin/haproxy:http")

        assert ok is True
        juju_cmd = next(c for c in calls if c[0] == "juju" and c[1] == "deploy" and "--resource" in c)
        assert "app-image=localhost:32000/myapp:0.2" in " ".join(juju_cmd)

    def test_success_includes_app_profiles_when_set(self, tmp_path):
        project = self._setup_project(
            tmp_path, charm_name="spring-petclinic_amd64", rock_name="spring-petclinic_0.1_amd64"
        )
        status = PipelineStatus(pipeline_id="d1p")
        calls = []

        def _fake_popen(cmd, **kwargs):
            calls.append(cmd)
            return _make_proc(returncode=0)

        with patch("subprocess.Popen", side_effect=_fake_popen), \
             patch.dict(os.environ, {"APP_PROFILES": "postgres"}):
            from studio_agent.stages import run_deploy

            ok = run_deploy(project, status, _cancel(), "d1p", "admin/haproxy:http")

        assert ok is True
        juju_cmd = next(c for c in calls if c[0] == "juju" and c[1] == "deploy" and "--resource" in c)
        assert "--config" in juju_cmd
        assert "app-profiles=postgres" in juju_cmd

    def test_add_model_called_first(self, tmp_path):
        project = self._setup_project(
            tmp_path, charm_name="myapp_amd64", rock_name="myapp_0.1_amd64"
        )
        status = PipelineStatus(pipeline_id="my-pipeline-id")
        calls = []

        def _fake_popen(cmd, **kwargs):
            calls.append(cmd)
            return _make_proc(returncode=0)

        with patch("subprocess.Popen", side_effect=_fake_popen):
            from studio_agent.stages import run_deploy

            ok = run_deploy(project, status, _cancel(), "my-pipeline-id", "admin/haproxy:http")

        assert ok is True
        first_juju = next(c for c in calls if c[0] == "juju")
        assert first_juju[1] == "add-model"
        assert "my-pipeline-id" in first_juju
        assert "ck8s" in first_juju

    def test_ingress_configurator_deployed_with_hostname(self, tmp_path):
        project = self._setup_project(
            tmp_path, charm_name="myapp_amd64", rock_name="myapp_0.1_amd64"
        )
        status = PipelineStatus(pipeline_id="my-pipeline-id")
        calls = []

        def _fake_popen(cmd, **kwargs):
            calls.append(cmd)
            return _make_proc(returncode=0)

        with patch("subprocess.Popen", side_effect=_fake_popen):
            from studio_agent.stages import run_deploy

            ok = run_deploy(project, status, _cancel(), "my-pipeline-id", "admin/haproxy:http")

        assert ok is True
        juju_cmds = [c for c in calls if c[0] == "juju"]
        ingress_cmd = next(c for c in juju_cmds if "ingress-configurator" in c)
        assert "hostname=my-pipeline-id.charmhub.studio" in " ".join(ingress_cmd)
        assert "--model" in ingress_cmd

    def test_haproxy_integration_issued(self, tmp_path):
        project = self._setup_project(
            tmp_path, charm_name="myapp_amd64", rock_name="myapp_0.1_amd64"
        )
        status = PipelineStatus(pipeline_id="my-pipeline-id")
        calls = []

        def _fake_popen(cmd, **kwargs):
            calls.append(cmd)
            return _make_proc(returncode=0)

        with patch("subprocess.Popen", side_effect=_fake_popen):
            from studio_agent.stages import run_deploy

            ok = run_deploy(project, status, _cancel(), "my-pipeline-id", "concierge-lxd:admin/haproxy.haproxy")

        assert ok is True
        juju_cmds = [c for c in calls if c[0] == "juju"]
        integrate_cmd = next(c for c in juju_cmds if "integrate" in c)
        assert "concierge-lxd:admin/haproxy.haproxy" in integrate_cmd
        assert "ingress-configurator:haproxy-route" in integrate_cmd
        assert "--model" in integrate_cmd


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
        call_count = 0

        def _fake_popen(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            # skopeo succeeds, juju fails
            rc = 0 if call_count == 1 else 1
            return _make_proc(returncode=rc, stderr="juju error" if rc else "")

        with patch("subprocess.Popen", side_effect=_fake_popen):
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
                str(tmp_path),
                "my-project",
                _cancel(),
            )
        assert ok is True
        assert path == str(tmp_path / "my-project")

    def test_git_clone_failure(self, tmp_path):
        with patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="auth failed")):
            from studio_agent.stages import run_clone

            ok, msg = run_clone(
                {"type": "git", "url": "https://github.com/org/repo.git"},
                str(tmp_path),
                "my-project",
                _cancel(),
            )
        assert ok is False
        assert "auth failed" in msg

    def test_git_clone_with_branch(self, tmp_path):
        with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            from studio_agent.stages import run_clone

            run_clone(
                {"type": "git", "url": "https://github.com/org/repo.git", "branch": "dev"},
                str(tmp_path),
                "proj",
                _cancel(),
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
