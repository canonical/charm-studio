#!/usr/bin/env python3

"""Detect likely 12-factor framework fit for a repository."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


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


def parse_pyproject(repo: Path) -> tuple[set[str], str]:
    deps: set[str] = set()
    path = repo / "pyproject.toml"
    if not path.exists():
        return deps, ""
    content = read_text(path)
    data = tomllib.loads(content)
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
    return deps, content


def normalize_name(name: str) -> str:
    return name.replace("-", "_").lower()


def has_pattern(path: Path, pattern: str) -> bool:
    if not path.exists():
        return False
    return re.search(pattern, read_text(path), re.MULTILINE) is not None


def score_frameworks(repo: Path) -> dict[str, dict[str, object]]:
    scores: dict[str, int] = defaultdict(int)
    signals: dict[str, list[str]] = defaultdict(list)

    pyproject_deps, _ = parse_pyproject(repo)
    deps = parse_requirements(repo) | pyproject_deps
    project_name = normalize_name(repo.name)

    def add(framework: str, score: int, signal: str) -> None:
        scores[framework] += score
        signals[framework].append(signal)

    if (repo / "go.mod").exists():
        add("go", 5, "found go.mod")

    for package_rel, base_score in ((Path("app/package.json"), 3), (Path("package.json"), 2)):
        package_path = repo / package_rel
        if not package_path.exists():
            continue
        try:
            package = json.loads(read_text(package_path))
        except json.JSONDecodeError:
            package = {}
        add("expressjs", base_score, f"found {package_rel}")
        if isinstance(package, dict):
            if package.get("name"):
                add("expressjs", 1, f"{package_rel} defines name")
            if package.get("scripts", {}).get("start"):
                add("expressjs", 2, f"{package_rel} defines scripts.start")
            package_deps = {
                *package.get("dependencies", {}).keys(),
                *package.get("devDependencies", {}).keys(),
            }
            if "express" in package_deps:
                add("expressjs", 2, f"{package_rel} depends on express")

    if any((repo / file).exists() for file in ("pom.xml", "build.gradle", "mvnw", "gradlew")):
        add("spring-boot", 3, "found Java build files or wrappers")
        for build_file in ("pom.xml", "build.gradle"):
            path = repo / build_file
            if path.exists() and "spring-boot" in read_text(path):
                add("spring-boot", 2, f"{build_file} mentions spring-boot")

    if "django" in deps:
        add("django", 4, "Python metadata includes django")
    if (repo / "manage.py").exists():
        add("django", 3, "found manage.py")
    for rel in (
        Path(project_name) / project_name / "wsgi.py",
        Path(project_name) / "mysite" / "wsgi.py",
    ):
        if has_pattern(repo / rel, r"\bapplication\b"):
            add("django", 2, f"found Django wsgi entrypoint at {rel}")

    if "flask" in deps:
        add("flask", 4, "Python metadata includes flask")
    for rel in (
        Path("app.py"),
        Path("main.py"),
        Path("app") / "__init__.py",
        Path("app") / "app.py",
        Path("app") / "main.py",
        Path("src") / "__init__.py",
        Path("src") / "app.py",
        Path("src") / "main.py",
        Path(project_name) / "__init__.py",
        Path(project_name) / "app.py",
        Path(project_name) / "main.py",
    ):
        path = repo / rel
        if not path.exists():
            continue
        if has_pattern(path, r"\bFlask\s*\(") or has_pattern(path, r"\b(create_app|make_app)\s*\("):
            add("flask", 2, f"found Flask entrypoint signal at {rel}")
            break

    if {"fastapi", "starlette"} & deps:
        add("fastapi", 4, "Python metadata includes fastapi or starlette")
    for rel in (
        Path("app.py"),
        Path("main.py"),
        Path("app") / "__init__.py",
        Path("app") / "app.py",
        Path("app") / "main.py",
        Path("src") / "__init__.py",
        Path("src") / "app.py",
        Path("src") / "main.py",
        Path(project_name) / "__init__.py",
        Path(project_name) / "app.py",
        Path(project_name) / "main.py",
    ):
        path = repo / rel
        if not path.exists():
            continue
        if has_pattern(path, r"^\s*app\s*=") and (
            "FastAPI" in read_text(path) or "Starlette" in read_text(path)
        ):
            add("fastapi", 2, f"found ASGI app signal at {rel}")
            break

    return {
        framework: {"score": score, "signals": signals[framework]}
        for framework, score in scores.items()
    }


def collect_web_signals(repo: Path, framework: str | None) -> tuple[list[str], list[str]]:
    if not framework:
        return [], []

    positive: list[str] = []
    negative: list[str] = []

    procfile = repo / "Procfile"
    if procfile.exists() and re.search(r"^\s*web\s*:", read_text(procfile), re.MULTILINE):
        positive.append("Procfile declares a web process")

    pyproject = repo / "pyproject.toml"
    if pyproject.exists():
        pyproject_text = read_text(pyproject)
        if re.search(r"(?m)^\s*\[project\.scripts\]\s*$", pyproject_text) or re.search(
            r"console_scripts", pyproject_text
        ):
            negative.append("pyproject.toml exposes console-style entry points")

    source_patterns = {
        "django": [r"\burlpatterns\b", r"\bpath\s*\(", r"\bre_path\s*\("],
        "expressjs": [r"\bapp\.(get|post|put|patch|delete|use)\s*\(", r"\brouter\.(get|post|put|patch|delete|use)\s*\("],
        "fastapi": [r"@(app|router)\.(get|post|put|patch|delete)\s*\("],
        "flask": [r"@app\.route\s*\(", r"\bFlask\s*\("],
        "go": [r"\bhttp\.Handle(Func)?\s*\(", r"\bgin\.(Default|New)\s*\(", r"\brouter\.(GET|POST|PUT|PATCH|DELETE)\s*\("],
        "spring-boot": [r"@(RestController|Controller)\b", r"@(Get|Post|Put|Delete|Request)Mapping\b"],
    }
    listen_patterns = [r"\blisten\s*\(", r"\bPORT\b", r"\bSERVER_PORT\b", r"\bUVICORN_PORT\b"]

    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".py", ".go", ".java", ".js", ".jsx", ".ts", ".tsx", ".kt", ".properties", ".yml", ".yaml"}:
            continue
        content = read_text(path)
        if any(re.search(pattern, content, re.MULTILINE) for pattern in source_patterns.get(framework, [])):
            positive.append(f"route or controller signal in {path.relative_to(repo)}")
            break
    else:
        if framework == "django" and (repo / "manage.py").exists():
            positive.append("manage.py suggests a Django web project")

    for path in repo.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".py", ".go", ".java", ".js", ".jsx", ".ts", ".tsx", ".kt", ".properties", ".yml", ".yaml"}:
            continue
        if any(re.search(pattern, read_text(path), re.MULTILINE) for pattern in listen_patterns):
            positive.append(f"listen-port signal in {path.relative_to(repo)}")
            break

    return positive, negative


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", help="Repository path to inspect")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    results = score_frameworks(repo)
    ordered = sorted(
        (
            {"framework": framework, **details}
            for framework, details in results.items()
        ),
        key=lambda item: (-int(item["score"]), str(item["framework"])),
    )
    detected = ordered[0]["framework"] if ordered else None
    web_positive, web_negative = collect_web_signals(repo, detected)
    web_app_guess = bool(detected and web_positive)

    notes: list[str] = []
    if not detected:
        notes.append("No supported framework was confidently detected.")
    elif not web_positive:
        notes.append("Framework detected, but web-service confidence is low. Confirm manually before proceeding.")
    if web_negative:
        notes.extend(web_negative)

    output = {
        "repo": str(repo),
        "supported": detected is not None,
        "web_app_guess": web_app_guess,
        "web_app_signals": {
            "positive": web_positive,
            "negative": web_negative,
        },
        "detected_framework": detected,
        "candidates": ordered,
        "notes": notes,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
