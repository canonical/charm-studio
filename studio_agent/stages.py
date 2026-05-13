from __future__ import annotations
import glob as _glob
import os
import subprocess
import tarfile
import threading
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

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
    src_type = source.get("type")
    try:
        if src_type == "git":
            cmd = ["git", "clone"]
            if source.get("branch"):
                cmd += ["--branch", source["branch"]]
            cmd += ["--", source["url"], project_path]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                return False, r.stderr
        elif src_type == "bitbucket":
            token = source.get("access_token", "")
            url = (
                f"https://x-token-auth:{token}@bitbucket.org/"
                f"{source['workspace']}/{source['repo_slug']}.git"
            )
            cmd = ["git", "clone"]
            if source.get("branch"):
                cmd += ["--branch", source["branch"]]
            cmd += ["--", url, project_path]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if r.returncode != 0:
                return False, r.stderr
        elif src_type == "url":
            archive_url = source["url"]
            tmp_path = project_path + ".download"
            urllib.request.urlretrieve(archive_url, tmp_path)
            os.makedirs(project_path, exist_ok=True)
            if archive_url.endswith(".zip"):
                with zipfile.ZipFile(tmp_path) as zf:
                    zf.extractall(project_path)
            else:
                with tarfile.open(tmp_path) as tf:
                    tf.extractall(project_path)
            os.remove(tmp_path)
        else:
            return False, f"Unknown source type: {src_type}"
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
        ["opencode", "run", "--skill", "12factor-fit"],
        project_path, stage, cancel_event,
    )


def run_12factor_charm(
    project_path: str,
    status: PipelineStatus,
    cancel_event: threading.Event,
) -> bool:
    stage = next(s for s in status.stages if s.name == "12factor-charm")
    stage.status = "running"
    return _run_cmd(
        ["opencode", "run", "--skill", "12factor-charm"],
        project_path, stage, cancel_event, timeout=600,
    )


def run_12factor_rock(
    project_path: str,
    status: PipelineStatus,
    cancel_event: threading.Event,
) -> bool:
    stage = next(s for s in status.stages if s.name == "12factor-rock")
    stage.status = "running"
    return _run_cmd(
        ["opencode", "run", "--skill", "12factor-rock"],
        project_path, stage, cancel_event, timeout=600,
    )


def run_deploy(
    project_path: str,
    status: PipelineStatus,
    cancel_event: threading.Event,
    pipeline_id: str,
    haproxy_offer: str,
) -> bool:
    stage = next(s for s in status.stages if s.name == "deploy")
    stage.status = "running"
    stage.started_at = _now()

    charm_files = _glob.glob(os.path.join(project_path, "*.charm"))
    rock_files = _glob.glob(os.path.join(project_path, "*.rock"))
    if not charm_files or not rock_files:
        stage.stderr = (
            f"Expected one .charm and one .rock file; "
            f"found charms={charm_files}, rocks={rock_files}"
        )
        stage.status = "failed"
        stage.finished_at = _now()
        return False

    charm_file = charm_files[0]
    rock_file = rock_files[0]
    rock_image = f"app-image={Path(rock_file).stem}"
    model = app = pipeline_id

    cmds = [
        ["juju", "add-model", model],
        [
            "juju", "deploy", f"./{Path(charm_file).name}", app,
            "--resource", rock_image, "-m", model,
        ],
        ["juju", "integrate", app, haproxy_offer],
    ]

    for cmd in cmds:
        r = subprocess.run(cmd, cwd=project_path, capture_output=True, text=True, timeout=300)
        stage.stdout += r.stdout
        stage.stderr += r.stderr
        if r.returncode != 0:
            stage.status = "failed"
            stage.finished_at = _now()
            return False
        if cancel_event.is_set():
            stage.status = "cancelled"
            stage.finished_at = _now()
            return False

    stage.status = "done"
    stage.finished_at = _now()
    status.result = PipelineResult(
        charm_file=charm_file,
        rock_file=rock_file,
        juju_model=model,
        juju_app=app,
    )
    return True
