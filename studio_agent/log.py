from __future__ import annotations

import logging
import logging.config


def configure_logging() -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["console"],
            },
            "loggers": {
                # Let uvicorn and huey logs flow through the same handler/format.
                "uvicorn": {"propagate": True},
                "uvicorn.access": {"propagate": True},
                "uvicorn.error": {"propagate": True},
                "huey": {"propagate": True},
            },
        }
    )
