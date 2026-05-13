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
    if stage.started_at is None:
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
    try:
        cmd = ["git", "clone"]
        if source.get("branch"):
            cmd += ["--branch", source["branch"]]
        cmd += ["--", source["url"], project_path]
        r = subprocess.run(cmd, cwd=workspace_base_dir, capture_output=True, text=True, timeout=300)
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


def run_charm_pack(
    project_path: str,
    status: PipelineStatus,
    cancel_event: threading.Event,
) -> bool:
    stage = next(s for s in status.stages if s.name == "12factor-charm")
    stage.status = "running"
    stage.stdout += "\n=== studio_agent: charmcraft pack ===\n"
    return _run_cmd(
        ["charmcraft", "pack"],
        project_path,
        stage,
        cancel_event,
        timeout=1200,
    )


def run_rock_pack(
    project_path: str,
    status: PipelineStatus,
    cancel_event: threading.Event,
) -> bool:
    stage = next(s for s in status.stages if s.name == "12factor-rock")
    stage.status = "running"
    stage.stdout += "\n=== studio_agent: rockcraft pack ===\n"
    return _run_cmd(
        ["rockcraft", "pack"],
        project_path,
        stage,
        cancel_event,
        timeout=1200,
    )


def run_deploy(
    project_path: str,
    status: PipelineStatus,
    cancel_event: threading.Event,
    juju_model: str,
    cloud_endpoint: str,
) -> bool:
    """Deploy the packed charm and rock via juju. Returns True on success."""
    from pathlib import Path

    stage = next(s for s in status.stages if s.name == "deploy")
    stage.status = "running"
    stage.started_at = _now()

    project = Path(project_path)
    charm_files = list(project.glob("*.charm"))
    rock_files = list(project.glob("*.rock"))

    if len(charm_files) != 1:
        stage.stderr += f"Expected one .charm file, found {len(charm_files)}"
        stage.status = "failed"
        stage.finished_at = _now()
        return False

    if len(rock_files) != 1:
        stage.stderr += f"Expected one .rock file, found {len(rock_files)}"
        stage.status = "failed"
        stage.finished_at = _now()
        return False

    charm_file = str(charm_files[0])
    rock_file = str(rock_files[0])

    r = subprocess.run(
        ["juju", "deploy", charm_file, "--model", juju_model],
        capture_output=True,
        text=True,
    )
    stage.stdout += r.stdout
    stage.stderr += r.stderr
    stage.finished_at = _now()

    if r.returncode != 0:
        stage.status = "failed"
        return False

    stage.status = "done"
    status.result = PipelineResult(
        charm_file=charm_file,
        rock_file=rock_file,
        juju_model=juju_model,
        juju_app=juju_model,
    )
    return True
