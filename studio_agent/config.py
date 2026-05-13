import os
import subprocess

def _snapctl_get(key: str) -> str:
    try:
        result = subprocess.run(
            ["snapctl", "get", key],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""

def get_workspace_base_dir() -> str:
    return _snapctl_get("workspace-base-dir") or os.environ.get("WORKSPACE_BASE_DIR", "/tmp/charm-studio-workspace")

def get_haproxy_offer() -> str:
    value = _snapctl_get("haproxy-offer") or os.environ.get("HAPROXY_OFFER", "")
    if not value:
        raise RuntimeError("snap config 'haproxy-offer' is not set")
    return value
