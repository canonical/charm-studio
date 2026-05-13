# Framework Detection

Use this file after running `scripts/detect_framework.py`.

## Supported Frameworks

- Flask
- Django
- FastAPI
- ExpressJS
- Go
- Spring Boot

## Primary Signals

### Flask

- `requirements.txt` or `pyproject.toml` includes `flask`
- Flask-style entrypoint in `app.py`, `main.py`, `app/`, `src/`, or `<project-name>/`

### Django

- `manage.py`
- Django dependency in Python metadata
- `wsgi.py` in `<project-name>/<project-name>/` or `<project-name>/mysite/`

### FastAPI

- `requirements.txt` or `pyproject.toml` includes `fastapi` or `starlette`
- ASGI `app` object in `app.py`, `main.py`, `app/`, `src/`, or `<project-name>/`

### ExpressJS

- `app/package.json`
- `package.json` has `name`
- `package.json` has `scripts.start`

### Go

- `go.mod`

### Spring Boot

- `pom.xml` or `build.gradle`
- `mvnw` or `gradlew`
- Spring Boot plugin or dependency signals in build files

## Use The Detector Output Correctly

- Treat the top candidate as the selected framework and proceed automatically.
- If two frameworks score similarly, pick the one with the stronger explicit
  signal (import statement in source > filename > directory name) and note
  the ambiguity in the fit verdict.
- Do not stop to confirm the framework with the user.

## Web-App Confirmation

Even if the framework is supported, verify the repo is meant to run as a web
service by inspecting source code for route or listener patterns. Do not treat
a CLI or worker-only app as a fit just because it uses a supported framework.
If no web entrypoint is found, stop with a clear error rather than asking.
Extra `-worker` or `-scheduler` services are fine when they accompany a main
web service.
