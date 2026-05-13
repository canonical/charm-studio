import os
import subprocess


def _snapctl_get(key: str) -> str:
    try:
        result = subprocess.run(
            ["snapctl", "get", key],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""


def get_workspace_base_dir() -> str:
    default = "/tmp/charm-studio-workspace"
    return _snapctl_get("workspace-base-dir") or os.environ.get("WORKSPACE_BASE_DIR", default)


def get_port() -> int:
    value = _snapctl_get("port") or os.environ.get("PORT", "")
    try:
        return int(value) if value else 8000
    except ValueError:
        return 8000


def get_haproxy_offer() -> str:
    value = _snapctl_get("haproxy-offer") or os.environ.get("HAPROXY_OFFER", "")
    if not value:
        raise RuntimeError("snap config 'haproxy-offer' is not set")
    return value


def get_registry() -> str:
    return _snapctl_get("registry") or os.environ.get("REGISTRY", "localhost:32000")


def get_app_profiles() -> str | None:
    return _snapctl_get("app-profiles") or os.environ.get("APP_PROFILES") or None
