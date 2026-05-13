import logging
import os
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .models import PipelineResult, PipelineStatus, Stage

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_oci_resource_name(project_path: str) -> str:
    """Return the OCI image resource name by reading the extension from charmcraft.yaml.

    Flask/Django use '<framework>-app-image'; all other paas-charm frameworks use 'app-image'.
    Falls back to 'app-image' if the file is missing or the extension is unrecognised.
    """
    _FRAMEWORK_IMAGE: dict[str, str] = {
        "flask-framework": "flask-app-image",
        "django-framework": "django-app-image",
    }
    candidates = [
        Path(project_path) / "charmcraft.yaml",
        Path(project_path) / "charm" / "charmcraft.yaml",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = yaml.safe_load(path.read_text()) or {}
            extensions = data.get("extensions", [])
            for ext in extensions:
                if ext in _FRAMEWORK_IMAGE:
                    return _FRAMEWORK_IMAGE[ext]
                if ext.endswith("-framework"):
                    return "app-image"
        except Exception:
            logger.warning("Could not parse %s to find OCI resource name", path)
    logger.warning(
        "Could not determine OCI resource name from charmcraft.yaml, falling back to 'app-image'"
    )
    return "app-image"

def _run_cmd(
    cmd: list[str],
    cwd: str,
    stage: Stage,
    cancel_event: threading.Event,
    timeout: int = 600,
    on_output=None,
) -> bool:
    """Run cmd, stream-capture output into stage. Returns True on success.

    If *on_output* is provided it is called after each chunk of output is
    appended so the caller can persist the updated status to disk.
    """
    if stage.started_at is None:
        stage.started_at = _now()
    logger.info("Stage %r starting: %s", stage.name, " ".join(cmd))
    try:
        proc = subprocess.Popen(
            cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        import os as _os
        import selectors
        import time

        # Make stdout/stderr non-blocking so selectors + read won't block
        import fcntl

        for fd in (proc.stdout, proc.stderr):
            flags = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, flags | _os.O_NONBLOCK)

        sel = selectors.DefaultSelector()
        sel.register(proc.stdout, selectors.EVENT_READ)
        sel.register(proc.stderr, selectors.EVENT_READ)

        start_time = time.monotonic()
        open_streams = 2

        while open_streams > 0:
            if cancel_event.is_set():
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                stage.stderr += "\nCancelled."
                stage.status = "cancelled"
                stage.finished_at = _now()
                logger.warning("Stage %r cancelled", stage.name)
                sel.close()
                return False

            if time.monotonic() - start_time > timeout:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                stage.stderr += f"\nTimed out after {timeout}s."
                stage.status = "failed"
                stage.finished_at = _now()
                logger.error("Stage %r timed out after %ds", stage.name, timeout)
                sel.close()
                return False

            ready = sel.select(timeout=2)
            flushed = False
            for key, _ in ready:
                data = key.fileobj.read(4096)
                if not data:
                    sel.unregister(key.fileobj)
                    open_streams -= 1
                    continue
                if key.fileobj is proc.stdout:
                    stage.stdout += data
                else:
                    stage.stderr += data
                flushed = True

            if flushed and on_output:
                on_output()

        proc.wait()
        sel.close()

        stage.finished_at = _now()
        if proc.returncode != 0:
            stage.status = "failed"
            logger.error("Stage %r failed (exit %d)", stage.name, proc.returncode)
            return False
        stage.status = "done"
        logger.info("Stage %r finished successfully", stage.name)
        return True
    except Exception as exc:
        stage.stderr += f"\n{exc}"
        stage.status = "failed"
        stage.finished_at = _now()
        logger.exception("Stage %r raised an exception", stage.name)
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
    on_status_change=None,
) -> bool:
    stage = next(s for s in status.stages if s.name == "verify")
    stage.status = "running"
    if on_status_change:
        on_status_change()
    return _run_cmd(
        [
            "opencode",
            "run",
            "/12factor-fit check if this local repository can be charmed using 12factor",
        ],
        project_path,
        stage,
        cancel_event,
        on_output=on_status_change,
    )


def run_12factor_charm(
    project_path: str,
    status: PipelineStatus,
    cancel_event: threading.Event,
    on_status_change=None,
) -> bool:
    stage = next(s for s in status.stages if s.name == "12factor-charm")
    stage.status = "running"
    if on_status_change:
        on_status_change()
    charm_prompt = (
        f"/12factor-charm charm this local repository,"
        f" output all files into {project_path}"
    )
    return _run_cmd(
        ["opencode", "run", charm_prompt],
        project_path,
        stage,
        cancel_event,
        timeout=600,
        on_output=on_status_change,
    )


def run_12factor_rock(
    project_path: str,
    status: PipelineStatus,
    cancel_event: threading.Event,
    on_status_change=None,
) -> bool:
    stage = next(s for s in status.stages if s.name == "12factor-rock")
    stage.status = "running"
    if on_status_change:
        on_status_change()
    rock_prompt = (
        f"/12factor-rock create a rock for this local repository,"
        f" output all files into {project_path}"
    )
    return _run_cmd(
        ["opencode", "run", rock_prompt],
        project_path,
        stage,
        cancel_event,
        timeout=600,
        on_output=on_status_change,
    )


def run_charm_pack(
    project_path: str,
    status: PipelineStatus,
    cancel_event: threading.Event,
    on_status_change=None,
) -> bool:
    stage = next(s for s in status.stages if s.name == "12factor-charm")
    stage.status = "running"
    stage.stdout += "\n=== studio_agent: charmcraft pack ===\n"
    if on_status_change:
        on_status_change()
    charm_subdir = Path(project_path) / "charm"
    cwd = str(charm_subdir) if (charm_subdir / "charmcraft.yaml").exists() else project_path
    return _run_cmd(
        ["charmcraft", "pack"],
        cwd,
        stage,
        cancel_event,
        timeout=1200,
        on_output=on_status_change,
    )


def run_rock_pack(
    project_path: str,
    status: PipelineStatus,
    cancel_event: threading.Event,
    on_status_change=None,
) -> bool:
    stage = next(s for s in status.stages if s.name == "12factor-rock")
    stage.status = "running"
    stage.stdout += "\n=== studio_agent: rockcraft pack ===\n"
    if on_status_change:
        on_status_change()
    return _run_cmd(
        ["rockcraft", "pack"],
        project_path,
        stage,
        cancel_event,
        timeout=1200,
        on_output=on_status_change,
    )


def run_deploy(
    project_path: str,
    status: PipelineStatus,
    cancel_event: threading.Event,
    juju_model: str,
    cloud_endpoint: str,
    on_status_change=None,
) -> bool:
    """Push the rock to the OCI registry then deploy charm + rock via juju."""
    from pathlib import Path

    from .config import get_app_profiles, get_registry

    stage = next(s for s in status.stages if s.name == "deploy")
    stage.status = "running"
    stage.started_at = _now()
    if on_status_change:
        on_status_change()

    project = Path(project_path)
    charm_subdir = project / "charm"
    charm_files = list(project.glob("*.charm")) or list(charm_subdir.glob("*.charm"))
    rock_files = list(project.glob("*.rock"))

    if len(charm_files) != 1:
        msg = f"Expected one .charm file, found {len(charm_files)}"
        stage.stderr += msg
        stage.status = "failed"
        stage.finished_at = _now()
        logger.error("Deploy: %s", msg)
        return False

    if len(rock_files) != 1:
        msg = f"Expected one .rock file, found {len(rock_files)}"
        stage.stderr += msg
        stage.status = "failed"
        stage.finished_at = _now()
        logger.error("Deploy: %s", msg)
        return False

    charm_file = charm_files[0]
    rock_file = rock_files[0]

    # Derive app name from charm stem: "<name>_<arch>.charm" → "<name>"
    app_name = charm_file.stem.rsplit("_", 1)[0]

    # Derive image tag from rock stem: "<name>_<version>_<arch>.rock" → "<name>:<version>"
    rock_parts = rock_file.stem.split("_")
    rock_name = rock_parts[0]
    rock_version = rock_parts[1] if len(rock_parts) > 2 else "latest"

    registry = get_registry()
    image_ref = f"{registry}/{rock_name}:{rock_version}"

    logger.info("Deploy: creating juju model %s", juju_model)
    if not _run_cmd(
        ["juju", "add-model", juju_model, "ck8s"],
        project_path,
        stage,
        cancel_event,
        timeout=60,
        on_output=on_status_change,
    ):
        return False

    logger.info("Deploy: pushing rock %s → %s", rock_file.name, image_ref)
    if not _run_cmd(
        [
            "rockcraft.skopeo",
            "copy",
            "--insecure-policy",
            "--dest-tls-verify=false",
            f"oci-archive:{rock_file}",
            f"docker://{image_ref}",
        ],
        project_path,
        stage,
        cancel_event,
        timeout=300,
        on_output=on_status_change,
    ):
        return False

    deploy_cmd = [
        "juju", "deploy",
        str(charm_file),
        app_name,
        "--model", juju_model,
        "--resource", f"{_get_oci_resource_name(project_path)}={image_ref}",
    ]
    if app_profiles := get_app_profiles():
        deploy_cmd += ["--config", f"app-profiles={app_profiles}"]

    logger.info("Deploy: %s  model=%s", " ".join(deploy_cmd), juju_model)
    if not _run_cmd(deploy_cmd, project_path, stage, cancel_event, timeout=300, on_output=on_status_change):
        return False

    # ── Deploy ingress-configurator ───────────────────────────────────────
    logger.info("Deploy: deploying ingress-configurator for pipeline %s", juju_model)
    if not _run_cmd(
        [
            "juju", "deploy",
            "ingress-configurator",
            "--trust",
            "--model", juju_model,
            "--config", f"hostname={juju_model}.charmhub.studio",
        ],
        project_path,
        stage,
        cancel_event,
        timeout=300,
        on_output=on_status_change,
    ):
        return False

    # ── Integrate ingress-configurator with haproxy ───────────────────────
    logger.info("Deploy: integrating ingress-configurator with haproxy offer %s", cloud_endpoint)
    if not _run_cmd(
        [
            "juju", "integrate",
            "--model", juju_model,
            cloud_endpoint,
            "ingress-configurator:haproxy-route",
        ],
        project_path,
        stage,
        cancel_event,
        timeout=300,
        on_output=on_status_change,
    ):
        return False

    # ── Integrate app with ingress-configurator ───────────────────────────
    logger.info("Deploy: integrating %s with ingress-configurator", app_name)
    if not _run_cmd(
        [
            "juju", "integrate",
            "--model", juju_model,
            app_name,
            "ingress-configurator",
        ],
        project_path,
        stage,
        cancel_event,
        timeout=300,
        on_output=on_status_change,
    ):
        return False

    stage.status = "done"
    logger.info("Deploy: juju deploy succeeded")
    status.result = PipelineResult(
        charm_file=str(charm_file),
        rock_file=str(rock_file),
        juju_model=juju_model,
        juju_app=app_name,
    )
    return True
