#!/usr/bin/env python3

"""Preflight the selected Kubernetes context, Juju controller, registry, and local tools."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import subprocess
import urllib.error
import urllib.parse
import urllib.request


EXPERIMENTAL_FRAMEWORKS = {"expressjs", "fastapi", "go", "spring-boot"}
ENV_REQUIREMENTS = {
    "rockcraft": "ROCKCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS",
    "charmcraft": "CHARMCRAFT_ENABLE_EXPERIMENTAL_EXTENSIONS",
}


def run_command(argv: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, capture_output=True, text=True, check=False)


def parse_snap_tracking(snap_name: str) -> dict[str, object]:
    snap_present = shutil.which("snap") is not None
    result: dict[str, object] = {"present": snap_present}
    if not snap_present:
        return result
    command = run_command(["snap", "list", snap_name])
    result["installed"] = command.returncode == 0
    if command.returncode != 0:
        result["stderr"] = command.stderr.strip() or None
        return result

    lines = [line.strip() for line in command.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        return result
    parts = lines[1].split()
    tracking = next((part for part in parts if "/" in part), None)
    result["tracking"] = tracking
    return result


def check_tool(name: str, snap_name: str | None = None) -> dict[str, object]:
    present = shutil.which(name) is not None
    result: dict[str, object] = {"command": name, "present": present}
    if snap_name:
        result["snap"] = parse_snap_tracking(snap_name)
    return result


def check_skopeo_tool() -> dict[str, object]:
    path = shutil.which("skopeo")
    embedded = "/snap/rockcraft/current/bin/skopeo"
    embedded_present = os.path.exists(embedded)
    result: dict[str, object] = {
        "command": "skopeo",
        "present": bool(path or embedded_present),
        "path": path,
        "rockcraft_embedded_path": embedded if embedded_present else None,
    }
    if not path and embedded_present:
        result["note"] = "Prefer the Rockcraft-shipped skopeo binary for OCI copy operations."
    return result


def registry_probe(target: str, timeout: float) -> dict[str, object]:
    probes: list[dict[str, object]] = []
    candidates: list[str] = []
    if "://" in target:
        candidates.append(target)
    else:
        candidates.extend([f"http://{target}", f"https://{target}"])

    for candidate in candidates:
        parsed = urllib.parse.urlparse(candidate)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        result: dict[str, object] = {
            "url": candidate,
            "host": host,
            "port": port,
        }
        try:
            with socket.create_connection((host, port), timeout=timeout):
                result["tcp"] = "ok"
        except OSError as exc:
            result["tcp"] = f"failed: {exc}"
            probes.append(result)
            continue
        try:
            with urllib.request.urlopen(f"{candidate.rstrip('/')}/v2/", timeout=timeout) as response:
                result["http"] = response.status
                result["ok"] = True
        except urllib.error.URLError as exc:
            result["http"] = f"failed: {exc}"
        probes.append(result)
        if result.get("ok"):
            return {
                "ok": True,
                "registry": target,
                "probes": probes,
                "note": "Registry reachability is verified at the host level. Credential path matching still needs app-specific review.",
            }
    return {
        "ok": False,
        "registry": target,
        "probes": probes,
        "note": "Registry reachability failed. Credential and path checks were not attempted.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kubectl-cmd", default="kubectl")
    parser.add_argument("--context")
    parser.add_argument("--framework", choices=sorted({"django", "expressjs", "fastapi", "flask", "go", "spring-boot"}))
    parser.add_argument("--juju-controller")
    parser.add_argument("--registry")
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args()

    checks: dict[str, object] = {}
    ok = True

    kubectl_present = shutil.which(args.kubectl_cmd) is not None
    checks["kubectl"] = {"command": args.kubectl_cmd, "present": kubectl_present}
    if kubectl_present:
        contexts_cmd = run_command([args.kubectl_cmd, "config", "get-contexts", "-o", "name"])
        current_cmd = run_command([args.kubectl_cmd, "config", "current-context"])
        contexts = [line.strip() for line in contexts_cmd.stdout.splitlines() if line.strip()]
        selected_ok = args.context in contexts if args.context else True
        checks["kubernetes_contexts"] = {
            "contexts": contexts,
            "current": current_cmd.stdout.strip() or None,
            "selected": args.context,
            "selected_ok": selected_ok,
        }
        if args.context and not selected_ok:
            ok = False
    else:
        ok = False

    juju_present = shutil.which("juju") is not None
    checks["juju"] = {"present": juju_present}
    if juju_present:
        controllers_cmd = run_command(["juju", "controllers", "--format", "json"])
        controllers = []
        if controllers_cmd.returncode == 0:
            data = json.loads(controllers_cmd.stdout or "{}")
            controllers = sorted(data.get("controllers", {}).keys())
        selected_ok = args.juju_controller in controllers if args.juju_controller else True
        checks["juju_controllers"] = {
            "controllers": controllers,
            "selected": args.juju_controller,
            "selected_ok": selected_ok,
        }
        if args.juju_controller and not selected_ok:
            ok = False
    else:
        ok = False

    checks["local_tools"] = {
        "rockcraft": check_tool("rockcraft", snap_name="rockcraft"),
        "charmcraft": check_tool("charmcraft", snap_name="charmcraft"),
        "skopeo": check_skopeo_tool(),
    }
    for tool_name, details in checks["local_tools"].items():
        if tool_name == "skopeo":
            continue
        if not details["present"]:
            ok = False

    if args.framework in EXPERIMENTAL_FRAMEWORKS:
        extension_checks: dict[str, object] = {
            "framework": args.framework,
            "experimental_required": True,
            "notes": [],
        }
        for tool_name, env_name in ENV_REQUIREMENTS.items():
            tool_details = checks["local_tools"][tool_name]
            env_value = os.environ.get(env_name, "")
            env_ok = env_value.lower() in {"1", "true", "yes"}
            snap_tracking = tool_details.get("snap", {}).get("tracking")
            tracking_ok = isinstance(snap_tracking, str) and snap_tracking.endswith("/edge")
            extension_checks[tool_name] = {
                "env_name": env_name,
                "env_value": env_value or None,
                "env_ok": env_ok,
                "tracking": snap_tracking,
                "tracking_ok": tracking_ok,
            }
            if not tool_details["present"] or not env_ok or not tracking_ok:
                ok = False
        checks["experimental_extensions"] = extension_checks

    if args.registry:
        registry = registry_probe(args.registry, timeout=args.timeout)
        checks["registry"] = registry
        ok = ok and bool(registry["ok"])

    print(json.dumps({"ok": ok, "checks": checks}, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
