#!/usr/bin/env python3

"""Check whether a repository fits the selected Rockcraft framework contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


SUPPORTED_BASES = {
    "flask": ["bare", "ubuntu@22.04", "ubuntu:22.04", "ubuntu@24.04"],
    "django": ["bare", "ubuntu@22.04", "ubuntu:22.04", "ubuntu@24.04"],
    "fastapi": ["bare", "ubuntu@24.04"],
    "expressjs": ["bare", "ubuntu@24.04"],
    "go": ["bare", "ubuntu@24.04"],
    "spring-boot": ["bare", "ubuntu@24.04"],
}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def normalize_name(name: str) -> str:
    return name.replace("-", "_").lower()


def _parse_requirement_file(path: Path, visited: set[Path]) -> set[str]:
    deps: set[str] = set()
    if path in visited or not path.exists():
        return deps
    visited.add(path)
    for raw_line in read_text(path).splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith(("-r ", "--requirement ")):
            include = line.split(maxsplit=1)[1].strip()
            deps |= _parse_requirement_file((path.parent / include).resolve(), visited)
            continue
        if line.startswith(("-", "git+", "http:", "https:")):
            continue
        name = re.split(r"[<>=!~\[]", line, 1)[0].strip().lower().replace("_", "-")
        if name:
            deps.add(name)
    return deps


def parse_requirements(repo: Path) -> set[str]:
    return _parse_requirement_file((repo / "requirements.txt").resolve(), set())


def parse_pyproject(repo: Path) -> set[str]:
    deps: set[str] = set()
    path = repo / "pyproject.toml"
    if not path.exists():
        return deps
    data = tomllib.loads(read_text(path))
    for item in data.get("project", {}).get("dependencies", []):
        name = re.split(r"[<>=!~\[]", str(item), 1)[0].strip().lower().replace("_", "-")
        if name:
            deps.add(name)
    poetry = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    if isinstance(poetry, dict):
        for name in poetry:
            lowered = str(name).strip().lower().replace("_", "-")
            if lowered and lowered != "python":
                deps.add(lowered)
    return deps


def has_pattern(path: Path, pattern: str) -> bool:
    return path.exists() and re.search(pattern, read_text(path), re.MULTILINE) is not None


def python_project_metadata_warnings(repo: Path) -> list[str]:
    warnings: list[str] = []
    has_project_metadata = (repo / "pyproject.toml").exists() or (repo / "setup.py").exists()
    if has_project_metadata:
        warnings.append("Python plugin will try to install the local project; validate `pip install .` during execution.")
    if has_project_metadata and (repo / "charm").exists():
        warnings.append("`pyproject.toml` or `setup.py` plus `charm/` can break Craft Python plugin metadata discovery; preflight this before build.")
    return warnings


def parse_go_module_name(repo: Path) -> str | None:
    go_mod = repo / "go.mod"
    if not go_mod.exists():
        return None
    for line in read_text(go_mod).splitlines():
        match = re.match(r"^\s*module\s+(\S+)\s*$", line)
        if match:
            return match.group(1)
    return None


def find_go_cmd_dirs(repo: Path) -> list[str]:
    cmd_root = repo / "cmd"
    if not cmd_root.exists():
        return []
    return sorted(
        str(path.relative_to(repo))
        for path in cmd_root.iterdir()
        if path.is_dir() and any(child.suffix == ".go" for child in path.rglob("*.go"))
    )


def check_flask(repo: Path) -> dict[str, object]:
    issues = []
    warnings = python_project_metadata_warnings(repo)
    deps = parse_requirements(repo) | parse_pyproject(repo)
    if "flask" not in deps:
        issues.append("Flask dependency not found in requirements.txt or pyproject.toml.")
    project = normalize_name(repo.name)
    candidates = [
        Path("app.py"),
        Path("main.py"),
        Path("app") / "__init__.py",
        Path("app") / "app.py",
        Path("app") / "main.py",
        Path("src") / "__init__.py",
        Path("src") / "app.py",
        Path("src") / "main.py",
        Path(project) / "__init__.py",
        Path(project) / "app.py",
        Path(project) / "main.py",
    ]
    if not any(
        has_pattern(repo / candidate, r"\bFlask\s*\(")
        or has_pattern(repo / candidate, r"\b(create_app|make_app)\s*\(")
        or has_pattern(repo / candidate, r"^\s*(app|application)\s*=")
        for candidate in candidates
    ):
        issues.append("No supported Flask WSGI entrypoint was found in the default search locations.")
    return {"issues": issues, "warnings": warnings}


def check_django(repo: Path) -> dict[str, object]:
    issues = []
    warnings = python_project_metadata_warnings(repo)
    if not (repo / "requirements.txt").exists():
        issues.append("Django rock requires a root requirements.txt.")
    project = normalize_name(repo.name)
    wsgi_paths = [
        repo / project / project / "wsgi.py",
        repo / project / "mysite" / "wsgi.py",
    ]
    if not any(has_pattern(path, r"\bapplication\b") for path in wsgi_paths):
        issues.append("No supported Django wsgi.py with `application` was found.")
        warnings.append(
            "Django extension expects the runtime app under <repo>/<project-name>/ with either <project-name>/wsgi.py or mysite/wsgi.py."
        )
    return {"issues": issues, "warnings": warnings}


def check_fastapi(repo: Path) -> dict[str, object]:
    issues = []
    warnings = python_project_metadata_warnings(repo)
    deps = parse_requirements(repo) | parse_pyproject(repo)
    if not deps:
        issues.append("FastAPI rock requires a root requirements.txt or pyproject.toml with dependencies.")
    elif not {"fastapi", "starlette"} & deps:
        issues.append("Python metadata must include fastapi or starlette.")
    project = normalize_name(repo.name)
    candidates = [
        Path("app.py"),
        Path("main.py"),
        Path("app") / "__init__.py",
        Path("app") / "app.py",
        Path("app") / "main.py",
        Path("src") / "__init__.py",
        Path("src") / "app.py",
        Path("src") / "main.py",
        Path(project) / "__init__.py",
        Path(project) / "app.py",
        Path(project) / "main.py",
    ]
    if not any(has_pattern(repo / candidate, r"^\s*app\s*=") for candidate in candidates):
        issues.append("No supported FastAPI ASGI `app` object was found in the default search locations.")
    return {"issues": issues, "warnings": warnings}


def check_expressjs(repo: Path) -> dict[str, object]:
    issues = []
    warnings = []
    package_json = repo / "app" / "package.json"
    if not package_json.exists():
        issues.append("ExpressJS rock requires app/package.json.")
        return {"issues": issues, "warnings": warnings}
    try:
        package = json.loads(read_text(package_json))
    except json.JSONDecodeError:
        issues.append("app/package.json is not valid JSON.")
        return {"issues": issues, "warnings": warnings}
    if not package.get("name"):
        issues.append("package.json must define `name`.")
    if not package.get("scripts", {}).get("start"):
        issues.append("package.json must define `scripts.start`.")
    warnings.append("Verify the app really wants to run from /app with `npm start` before proceeding.")
    return {"issues": issues, "warnings": warnings}


def check_go(repo: Path) -> dict[str, object]:
    issues = []
    warnings = []
    if not (repo / "go.mod").exists():
        issues.append("Go rock requires go.mod in the repository root.")
        return {"issues": issues, "warnings": warnings}

    module_name = parse_go_module_name(repo)
    cmd_dirs = find_go_cmd_dirs(repo)
    rock_name = repo.name
    if cmd_dirs:
        warnings.append(f"Detected Go main-package directories: {', '.join(cmd_dirs)}.")
    if module_name:
        warnings.append(f"Detected Go module path: {module_name}.")
    if cmd_dirs and all(Path(path).name != rock_name for path in cmd_dirs):
        warnings.append(
            "No cmd/* directory matches the rock name; if you override the service command, add an explicit go-framework/install-app.organize mapping."
        )
    else:
        warnings.append("If the built binary name differs from the rock name, adjust organize in go-framework/install-app.")
    return {"issues": issues, "warnings": warnings}


def check_spring_boot(repo: Path) -> dict[str, object]:
    issues = []
    warnings = []
    pom = repo / "pom.xml"
    gradle = repo / "build.gradle"
    mvnw = repo / "mvnw"
    gradlew = repo / "gradlew"
    if pom.exists() and gradle.exists():
        issues.append("Spring Boot extension rejects repositories that expose both pom.xml and build.gradle.")
    if mvnw.exists() and gradlew.exists():
        issues.append("Spring Boot extension rejects repositories that expose both mvnw and gradlew.")
    if not pom.exists() and not gradle.exists():
        issues.append("Spring Boot extension requires pom.xml or build.gradle.")
    for wrapper in (mvnw, gradlew):
        if wrapper.exists() and not wrapper.stat().st_mode & 0o111:
            issues.append(f"{wrapper.name} exists but is not executable.")
    warnings.append("If both Maven and Gradle exist in upstream, ask the user which build path to keep in the trial copy.")
    return {"issues": issues, "warnings": warnings}


CHECKS = {
    "flask": check_flask,
    "django": check_django,
    "fastapi": check_fastapi,
    "expressjs": check_expressjs,
    "go": check_go,
    "spring-boot": check_spring_boot,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", help="Repository path")
    parser.add_argument("--framework", required=True, choices=sorted(CHECKS))
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    check = CHECKS[args.framework](repo)
    fit = not check["issues"]
    output = {
        "repo": str(repo),
        "framework": args.framework,
        "fit": fit,
        "supported_bases": SUPPORTED_BASES[args.framework],
        "issues": check["issues"],
        "warnings": check["warnings"],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if fit else 1


if __name__ == "__main__":
    raise SystemExit(main())
