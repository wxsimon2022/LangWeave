"""HTTP interface adapters."""

from app.interfaces.http.router import include_business_routers, router

__all__ = ["router", "include_business_routers"]
