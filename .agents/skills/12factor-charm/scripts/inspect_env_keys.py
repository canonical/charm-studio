#!/usr/bin/env python3

"""Inspect likely environment-variable keys used by an application source tree."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

PATTERNS = {
    "python": [
        re.compile(r"""os\.getenv\(\s*["']([A-Z0-9_]+)["']"""),
        re.compile(r"""os\.environ(?:\.get)?\(\s*["']([A-Z0-9_]+)["']"""),
        re.compile(r"""os\.environ\[\s*["']([A-Z0-9_]+)["']\s*\]"""),
    ],
    "javascript": [
        re.compile(r"""process\.env\.([A-Z][A-Z0-9_]*)"""),
        re.compile(r"""process\.env\[\s*["']([A-Z0-9_]+)["']\s*\]"""),
    ],
    "go": [
        re.compile(r"""os\.(?:Getenv|LookupEnv)\(\s*"([A-Z0-9_]+)"\s*\)"""),
    ],
    "java": [
        re.compile(r"""System\.getenv\(\s*"([A-Z0-9_]+)"\s*\)"""),
    ],
    "java_spring": [
        re.compile(r"""\$\{([A-Z][A-Z0-9_.]+)\}"""),
        re.compile(r"""@Value\(\s*"\$\{([^}:]+)(?::[^}]*)?\}"\s*\)"""),
    ],
    "dotenv": [
        re.compile(r"""^([A-Z][A-Z0-9_]+)\s*=""", re.MULTILINE),
    ],
}

ALLOWED_SUFFIXES = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".kt", ".yaml", ".yml", ".properties"}
IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "target",
    ".tox",
    ".mypy_cache",
    "__pycache__",
}

FRAMEWORK_CONTRACTS = {
    "flask": {
        "built_in_env_examples": ["FLASK_DEBUG", "FLASK_ENV", "FLASK_SECRET_KEY"],
        "user_config_prefix": "FLASK_",
        "relation_env_families": ["POSTGRESQL_DB_*", "MYSQL_DB_*", "REDIS_*", "SMTP_*", "OTEL_*"],
    },
    "django": {
        "built_in_env_examples": ["DJANGO_DEBUG", "DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS"],
        "user_config_prefix": "DJANGO_",
        "relation_env_families": ["POSTGRESQL_DB_*", "MYSQL_DB_*", "REDIS_*", "SMTP_*", "OTEL_*"],
    },
    "fastapi": {
        "built_in_env_examples": ["UVICORN_PORT", "UVICORN_HOST", "WEB_CONCURRENCY", "UVICORN_LOG_LEVEL", "APP_SECRET_KEY"],
        "user_config_prefix": "APP_",
        "relation_env_families": ["POSTGRESQL_DB_*", "MYSQL_DB_*", "REDIS_*", "SMTP_*", "OTEL_*"],
    },
    "expressjs": {
        "built_in_env_examples": ["PORT", "NODE_ENV", "APP_SECRET_KEY"],
        "user_config_prefix": "APP_",
        "relation_env_families": ["POSTGRESQL_DB_*", "MYSQL_DB_*", "REDIS_*", "SMTP_*", "OTEL_*"],
    },
    "go": {
        "built_in_env_examples": ["APP_PORT", "APP_METRICS_PORT", "APP_SECRET_KEY"],
        "user_config_prefix": "APP_",
        "relation_env_families": ["POSTGRESQL_DB_*", "MYSQL_DB_*", "REDIS_*", "SMTP_*", "OTEL_*"],
    },
    "spring-boot": {
        "built_in_env_examples": ["SERVER_PORT", "APP_PROFILES", "MANAGEMENT_SERVER_PORT", "spring.datasource.url"],
        "user_config_prefix": "APP_",
        "relation_env_families": ["POSTGRESQL_DB_*", "MYSQL_DB_*", "REDIS_*", "SMTP_*", "spring.security.oauth2.*"],
    },
}


def is_allowed_file(path: Path) -> bool:
    if path.suffix in ALLOWED_SUFFIXES:
        return True
    return path.name == ".env" or path.name.startswith(".env.")


def iter_files(repo: Path) -> list[Path]:
    files: list[Path] = []
    for path in repo.rglob("*"):
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.is_file() and is_allowed_file(path):
            files.append(path)
    return files


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="ignore")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", help="Repository path")
    parser.add_argument("--framework", choices=sorted(FRAMEWORK_CONTRACTS))
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    matches: dict[str, set[str]] = defaultdict(set)
    env_keys: set[str] = set()

    for path in iter_files(repo):
        content = read_text(path)
        for regexes in PATTERNS.values():
            for regex in regexes:
                for match in regex.findall(content):
                    if isinstance(match, tuple):
                        key = match[0]
                    else:
                        key = match
                    env_keys.add(key)
                    matches[str(path.relative_to(repo))].add(key)

    output = {
        "repo": str(repo),
        "framework": args.framework,
        "detected_env_keys": sorted(env_keys),
        "per_file": {path: sorted(keys) for path, keys in sorted(matches.items())},
    }
    if args.framework:
        output["framework_contract"] = FRAMEWORK_CONTRACTS[args.framework]
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
