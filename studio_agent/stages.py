import os
import subprocess
import threading
from datetime import datetime, timezone

from .models import PipelineResult, PipelineStatus, Stage


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_cmd(
    cmd: list[str],
    cwd: str,
    stage: Stage,
    cancel_event: threading.Event,
    timeout: int = 600,
) -> bool:
    """Run cmd, stream-capture output into stage. Returns True on success."""
    stage.started_at = _now()
    try:
        proc = subprocess.Popen(
            cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        while True:
            try:
                stdout, stderr = proc.communicate(timeout=2)
                break
            except subprocess.TimeoutExpired:
                if cancel_event.is_set():
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    stage.stderr += "\nCancelled."
                    stage.status = "cancelled"
                    stage.finished_at = _now()
                    return False

        stage.stdout += stdout
        stage.stderr += stderr
        stage.finished_at = _now()
        if proc.returncode != 0:
            stage.status = "failed"
            return False
        stage.status = "done"
        return True
    except Exception as exc:
        stage.stderr += f"\n{exc}"
        stage.status = "failed"
        stage.finished_at = _now()
        return False


def run_clone(
    source: dict,
    workspace_base_dir: str,
    project_id: str,
    cancel_event: threading.Event,
) -> tuple[bool, str]:
    """Clone / download source into workspace_base_dir/project_id.
    Returns (success, project_path_or_error_message).
    """
    project_path = os.path.join(workspace_base_dir, project_id)
    os.makedirs(workspace_base_dir, exist_ok=True)
    try:
        cmd = ["git", "clone"]
        if source.get("branch"):
            cmd += ["--branch", source["branch"]]
        cmd += ["--", source["url"], project_path]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return False, r.stderr
    except Exception as exc:
        return False, str(exc)
    return True, project_path


def run_verify(
    project_path: str,
    status: PipelineStatus,
    cancel_event: threading.Event,
) -> bool:
    stage = next(s for s in status.stages if s.name == "verify")
    stage.status = "running"
    return _run_cmd(
        [
            "opencode",
            "run",
            "/12factor-fit check if this local repository can be charmed using 12factor",
        ],
        project_path,
        stage,
        cancel_event,
    )


def run_12factor_charm(
    project_path: str,
    status: PipelineStatus,
    cancel_event: threading.Event,
) -> bool:
    stage = next(s for s in status.stages if s.name == "12factor-charm")
    stage.status = "running"
    return _run_cmd(
        ["opencode", "run", "/12factor-charm charm this local repository"],
        project_path,
        stage,
        cancel_event,
        timeout=600,
    )


def run_12factor_rock(
    project_path: str,
    status: PipelineStatus,
    cancel_event: threading.Event,
) -> bool:
    stage = next(s for s in status.stages if s.name == "12factor-rock")
    stage.status = "running"
    return _run_cmd(
        ["opencode", "run", "/12factor-rock create a rock for this local repository"],
        project_path,
        stage,
        cancel_event,
        timeout=600,
    )


def run_deploy(status: PipelineStatus) -> bool:
    stage = next(s for s in status.stages if s.name == "deploy")
    stage.status = "done"
    stage.finished_at = _now()
    status.result = PipelineResult(
        charm_file="",
        rock_file="",
        juju_model="",
        juju_app="",
    )
    return True
