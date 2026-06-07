"""Declarative base for all ORM models with built-in CRUD helpers.

All timestamp columns use ``DateTime(timezone=True)`` so that SQLAlchemy
stores UTC-aware values regardless of the server's ``time_zone`` setting.

CRUD usage
----------
    user = User.get(session, 1)                  # read by PK
    users = User.get_all(session, is_admin=True)  # list with filters

    u = User(username="new", ...).save(session)   # create
    u.is_admin = True
    u.save(session)                                # update (dirty tracking)

    u.delete(session)                              # delete
    session.commit()                               # caller controls commit
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    """Base class for all mapped ORM models.

    Provides four convenience methods that map to the four basic CRUD
    operations.  They operate on an **injected** session — the caller
    still controls ``session.commit()`` so that multiple operations can
    be grouped in a single transaction.
    """

    __abstract__ = True

    # ── Read ──────────────────────────────────────────────────────────

    @classmethod
    def get(cls, session: Session, ident: Any) -> Any | None:
        """Fetch a single record by primary key.

        Shorthand for ``session.get(Model, pk)``.
        """
        return session.get(cls, ident)

    @classmethod
    def get_all(
        cls,
        session: Session,
        *,
        order_by: Any = None,
        limit: int | None = None,
        offset: int = 0,
        **filters: Any,
    ) -> Sequence[Any]:
        """List records with optional equality filters.

        Examples
        --------
            User.get_all(session)                          # all users
            User.get_all(session, is_admin=True)            # filtered
            User.get_all(session, order_by=User.id.desc())  # ordered
            User.get_all(session, limit=10, offset=20)      # paginated
        """
        stmt = select(cls)
        for attr, value in filters.items():
            stmt = stmt.where(getattr(cls, attr) == value)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        if limit is not None:
            stmt = stmt.limit(limit).offset(offset)
        return session.scalars(stmt).all()

    # ── Create / Update ───────────────────────────────────────────────

    def save(self, session: Session) -> Any:
        """Insert (new) or update (existing) this record.

        Delegates to ``session.add()`` — the caller must call
        ``session.commit()`` afterwards.
        """
        session.add(self)
        return self

    # ── Delete ────────────────────────────────────────────────────────

    def delete(self, session: Session) -> None:
        """Delete this record from the database."""
        session.delete(self)
