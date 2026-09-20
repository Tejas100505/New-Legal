"""
Structured logging configuration using loguru.

- Development: pretty-printed colored output
- Production: structured JSON for log aggregators
- Request-ID correlation via loguru contextualize
"""

from __future__ import annotations

import sys

from loguru import logger

from app.config import Environment, get_settings


def setup_logging() -> None:
    """Configure loguru based on the current environment."""
    settings = get_settings()

    # Remove default handler
    logger.remove()

    if settings.app_env == Environment.PRODUCTION:
        # Structured JSON for production log aggregation
        logger.add(
            sys.stdout,
            level=settings.app_log_level.upper(),
            format="{message}",
            serialize=True,
        )
    else:
        # Pretty-printed colored output for development
        logger.add(
            sys.stderr,
            level=settings.app_log_level.upper(),
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<blue>{extra[request_id]}</blue> | "
                "{message}"
            ),
            filter=lambda record: "request_id" in record["extra"],
            colorize=True,
        )
        # Fallback handler for logs without request_id
        logger.add(
            sys.stderr,
            level=settings.app_log_level.upper(),
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "{message}"
            ),
            filter=lambda record: "request_id" not in record["extra"],
            colorize=True,
        )

    logger.info(
        "Logging configured",
        env=settings.app_env.value,
        level=settings.app_log_level,
    )
