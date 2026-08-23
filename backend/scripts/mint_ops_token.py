# backend/scripts/mint_ops_token.py
"""Mint a long-lived JWT for the ops console.

There's no identity/login flow yet (KICKOFF's identity context - Owner,
Agent, OTP claim - isn't built). Until it is, this is how the single
operator running Wizard-of-Oz gets a bearer token: run this once, paste
the output into the ops console's token screen.
"""

from __future__ import annotations

import sys
from datetime import timedelta

sys.path.insert(0, "src")

from naka.shared.api.security import create_access_token  # noqa: E402
from naka.shared.infrastructure.settings import Settings  # noqa: E402


def main() -> None:
    settings = Settings()
    token = create_access_token(
        subject="ops-console",
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expires_in=timedelta(days=30),
    )
    print(token)


if __name__ == "__main__":
    main()
