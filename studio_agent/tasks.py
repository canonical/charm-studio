from __future__ import annotations

import os
import threading
from pathlib import Path

from huey import SqliteHuey

from .config import get_haproxy_offer, get_workspace_base_dir
from .models import PipelineStatus
from .stages import (
    run_12factor_charm,
    run_12factor_rock,
    run_charm_pack,
    run_clone,
    run_deploy,
    run_rock_pack,
    run_verify,
)

huey = SqliteHuey(
    filename=os.environ.get(
        "HUEY_DB",
        os.path.join(os.environ.get("SNAP_COMMON", "/tmp"), "charm-studio-huey.db"),
    )
)

_STATUS_FILENAME = "pipeline_status.json"
_CANCEL_FILENAME = ".cancel"


def _status_path(workspace_base_dir: str, pipeline_id: str) -> str:
    return os.path.join(workspace_base_dir, f"{pipeline_id}-{_STATUS_FILENAME}")


def _cancel_path(workspace_base_dir: str, pipeline_id: str) -> str:
    return os.path.join(workspace_base_dir, f"{pipeline_id}-{_CANCEL_FILENAME}")


def save_status(workspace_base_dir: str, pipeline_id: str, status: PipelineStatus) -> None:
    path = _status_path(workspace_base_dir, pipeline_id)
    os.makedirs(workspace_base_dir, exist_ok=True)
    with open(path, "w") as f:
        f.write(status.model_dump_json())


def load_status(workspace_base_dir: str, pipeline_id: str) -> PipelineStatus | None:
    path = _status_path(workspace_base_dir, pipeline_id)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return PipelineStatus.model_validate_json(f.read())


def request_cancel(workspace_base_dir: str, pipeline_id: str) -> None:
    Path(_cancel_path(workspace_base_dir, pipeline_id)).touch()


def is_cancel_requested(workspace_base_dir: str, pipeline_id: str) -> bool:
    return os.path.exists(_cancel_path(workspace_base_dir, pipeline_id))


@huey.task()
def run_pipeline(pipeline_id: str, source: dict) -> None:
    workspace_base_dir = get_workspace_base_dir()

    status = PipelineStatus(pipeline_id=pipeline_id)
    save_status(workspace_base_dir, pipeline_id, status)

    cancel_event = threading.Event()

    def _watch_cancel() -> None:
        import time

        while not status.done:
            if is_cancel_requested(workspace_base_dir, pipeline_id):
                cancel_event.set()
                return
            time.sleep(1)

    watcher = threading.Thread(target=_watch_cancel, daemon=True)
    watcher.start()

    project_path = os.path.join(workspace_base_dir, pipeline_id)

    def _fail(msg: str) -> None:
        status.done = True
        status.error = msg
        save_status(workspace_base_dir, pipeline_id, status)

    def _save() -> None:
        save_status(workspace_base_dir, pipeline_id, status)

    # ── Clone ──────────────────────────────────────────────────────────────
    print("Cloning the repo: ", source)
    ok, result = run_clone(source, workspace_base_dir, pipeline_id, cancel_event)
    if not ok:
        return _fail(f"Clone failed: {result}")
    project_path = result
    _save()

    if cancel_event.is_set():
        return _fail("Cancelled before verify.")

    # ── Stage 1: verify ───────────────────────────────────────────────────
    print("12F fit: the repo: ", source)
    if not run_verify(project_path, status, cancel_event):
        stage = next(s for s in status.stages if s.name == "verify")
        return _fail(stage.stderr or "verify failed")
    _save()

    if cancel_event.is_set():
        return _fail("Cancelled after verify.")

    # ── Stage 2: 12factor-charm + 12factor-rock (parallel) ────────────────
    charm_ok = rock_ok = False
    charm_exc = rock_exc = None

    print("12F charm: the repo: ", source)

    def _run_charm():
        nonlocal charm_ok, charm_exc
        try:
            charm_ok = run_12factor_charm(project_path, status, cancel_event)
        except Exception as e:
            charm_exc = e
        _save()

    print("12F rock: the repo: ", source)

    def _run_rock():
        nonlocal rock_ok, rock_exc
        try:
            rock_ok = run_12factor_rock(project_path, status, cancel_event)
        except Exception as e:
            rock_exc = e
        _save()

    t_charm = threading.Thread(target=_run_charm)
    t_rock = threading.Thread(target=_run_rock)
    t_charm.start()
    t_rock.start()
    t_charm.join()
    t_rock.join()

    if not charm_ok:
        stage = next(s for s in status.stages if s.name == "12factor-charm")
        return _fail(stage.stderr or str(charm_exc) or "12factor-charm failed")
    if not rock_ok:
        stage = next(s for s in status.stages if s.name == "12factor-rock")
        return _fail(stage.stderr or str(rock_exc) or "12factor-rock failed")

    # # ── Studio packaging handoff: run pack commands after both skills finish ──
    # if not run_charm_pack(project_path, status, cancel_event):
    #     stage = next(s for s in status.stages if s.name == "12factor-charm")
    #     return _fail(stage.stderr or "charmcraft pack failed")
    # _save()

    # if not run_rock_pack(project_path, status, cancel_event):
    #     stage = next(s for s in status.stages if s.name == "12factor-rock")
    #     return _fail(stage.stderr or "rockcraft pack failed")
    # _save()

    if cancel_event.is_set():
        return _fail("Cancelled after 12factor stages.")

    # ── Stage 3: deploy ───────────────────────────────────────────────────
    try:
        haproxy_offer = get_haproxy_offer()
    except RuntimeError as e:
        return _fail(str(e))

    if not run_deploy(project_path, status, cancel_event, pipeline_id, haproxy_offer):
        stage = next(s for s in status.stages if s.name == "deploy")
        return _fail(stage.stderr or "deploy failed")

    status.done = True
    _save()
