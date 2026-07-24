#!/usr/bin/env python3
"""Reset or create the admin user password.

Usage:
    python scripts/reset_admin_password.py            # prompts for password
    python scripts/reset_admin_password.py --pass "newpass"
    python scripts/reset_admin_password.py --user admin --pass "newpass"
"""
from __future__ import annotations

from __future__ import annotations

import argparse
import getpass
import os
import sys

# Ensure the project root is on sys.path so that ``app`` and ``langweave``
# are importable regardless of how the script is invoked.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from app.application.security import hash_password
from app.infrastructure.persistence.database import get_session_factory
from app.infrastructure.persistence.user import User


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset admin password")
    parser.add_argument("--user", default="admin", help="Username (default: admin)")
    parser.add_argument("--pass", dest="password", help="New password")
    args = parser.parse_args()

    password = args.password
    if not password:
        password = getpass.getpass("New password: ")
        confirm = getpass.getpass("Confirm: ")
        if password != confirm:
            print("Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    password_hash = hash_password(password)

    session_factory = get_session_factory()
    with session_factory() as session:
        user = session.query(User).filter(User.username == args.user).first()
        if user is None:
            user = User(
                username=args.user,
                password_hash=password_hash,
                is_admin=True,
            )
            session.add(user)
            print(f"User '{args.user}' created with admin privileges.")
        else:
            user.password_hash = password_hash
            user.is_admin = True
            print(f"Password updated for user '{args.user}'.")
        session.commit()
        print("Done.")


if __name__ == "__main__":
    main()
