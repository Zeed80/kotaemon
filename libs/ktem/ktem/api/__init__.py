"""REST API для внешних агентов (OpenClaw и др.)."""

from .routes import router as api_router

__all__ = ["api_router"]
