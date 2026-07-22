"""
Structured logging configuration using structlog.

Call configure_logging() once at application startup.
Use get_logger() anywhere to obtain a bound logger.
"""

import logging
import sys
import structlog

import re


def redact_secrets(logger, log_method, event_dict):
    """Redact sensitive information from log events."""
    # Regex to match postgresql://user:password@host
    url_pattern = re.compile(
        r"(?P<scheme>\w+://)(?P<user>[^:]+):(?P<password>[^@]+)@(?P<rest>.*)"
    )

    for key, value in event_dict.items():
        if isinstance(value, str):
            # Redact URLs
            if "://" in value and "@" in value:
                event_dict[key] = url_pattern.sub(
                    r"\g<scheme>\g<user>:***@\g<rest>", value
                )
            # Redact session tokens or CSRF tokens if explicitly logged
            if key.lower() in (
                "session_id",
                "csrf_token",
                "password",
                "token",
                "secret",
            ):
                event_dict[key] = "***"
    return event_dict


def configure_logging() -> None:
    """Configure structlog with environment-appropriate renderer."""
    # Import settings here to avoid circular imports at module load time
    from app.core.config import get_settings

    settings = get_settings()

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        redact_secrets,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.APP_ENV == "production":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )


def get_logger() -> structlog.stdlib.BoundLogger:
    """Return a structlog bound logger."""
    return structlog.get_logger()  # type: ignore[return-value]
