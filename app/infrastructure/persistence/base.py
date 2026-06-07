"""Declarative base for all ORM models.

All timestamp columns use ``DateTime(timezone=True)`` so that SQLAlchemy
stores UTC-aware values regardless of the server's ``time_zone`` setting.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all mapped ORM models."""
