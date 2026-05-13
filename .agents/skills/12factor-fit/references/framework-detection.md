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

- Treat the top candidate as a proposal, not as permission to proceed silently.
- Confirm the framework with the user before generating rocks or charms.
- If two frameworks score similarly, stop and explain the ambiguity.

## Web-App Confirmation

Even if the framework is supported, confirm the repo is meant to run as a web
service. Do not treat a CLI or worker-only app as a fit just because it uses a
supported framework. Extra `-worker` or `-scheduler` services are fine when
they accompany a main web service.
