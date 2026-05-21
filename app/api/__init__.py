"""Compatibility exports for legacy API imports."""

from app.interfaces.http import include_business_routers, router

__all__ = ["router", "include_business_routers"]
