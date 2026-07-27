"""
Security utilities including account lockout and rate limiting.
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from prometheus_client import Counter

from src.db.models import User
from src.config.logging import get_logger

logger = get_logger(__name__)

# Metrics
FAILED_LOGIN_ATTEMPTS = Counter(
    "failed_login_attempts_total", "Total failed login attempts", ["email"]
)

ACCOUNT_LOCKOUTS = Counter("account_lockouts_total", "Total account lockouts", ["email"])


@dataclass
class LoginAttempt:
    """Login attempt record."""

    email: str
    attempt_time: datetime
    ip_address: str
    success: bool


class AccountLockout:
    """Account lockout manager."""

    def __init__(self, max_attempts: int = 5, lockout_duration_minutes: int = 30):
        self.max_attempts = max_attempts
        self.lockout_duration = timedelta(minutes=lockout_duration_minutes)
        self._attempts: dict[str, list[LoginAttempt]] = {}

    def record_attempt(self, email: str, ip_address: str, success: bool) -> dict:
        """Record a login attempt."""
        now = datetime.now(timezone.utc)

        if email not in self._attempts:
            self._attempts[email] = []

        # Clean old attempts
        cutoff = now - self.lockout_duration
        self._attempts[email] = [a for a in self._attempts[email] if a.attempt_time > cutoff]

        # Add new attempt
        attempt = LoginAttempt(
            email=email, attempt_time=now, ip_address=ip_address, success=success
        )
        self._attempts[email].append(attempt)

        # Update metrics
        if not success:
            FAILED_LOGIN_ATTEMPTS.labels(email=email).inc()

        # Check if should lockout
        recent_failures = [
            a for a in self._attempts[email] if not a.success and a.attempt_time > cutoff
        ]

        is_locked = len(recent_failures) >= self.max_attempts

        if is_locked and not success:
            ACCOUNT_LOCKOUTS.labels(email=email).inc()
            logger.warning(
                "account_locked", email=email, ip_address=ip_address, attempts=len(recent_failures)
            )

        return {
            "attempts": len(recent_failures),
            "max_attempts": self.max_attempts,
            "is_locked": is_locked,
            "lockout_until": now + self.lockout_duration if is_locked else None,
        }

    def is_locked(self, email: str) -> tuple[bool, Optional[datetime]]:
        """Check if account is locked."""
        if email not in self._attempts:
            return False, None

        now = datetime.now(timezone.utc)
        cutoff = now - self.lockout_duration

        # Clean old attempts
        self._attempts[email] = [a for a in self._attempts[email] if a.attempt_time > cutoff]

        # Count recent failures
        recent_failures = [a for a in self._attempts[email] if not a.success]

        if len(recent_failures) >= self.max_attempts:
            # Find the most recent failure
            last_failure = max(recent_failures, key=lambda a: a.attempt_time)
            lockout_until = last_failure.attempt_time + self.lockout_duration

            if lockout_until > now:
                return True, lockout_until

        return False, None

    def unlock(self, email: str) -> None:
        """Manually unlock an account."""
        if email in self._attempts:
            self._attempts[email] = []


# Global lockout manager
lockout_manager = AccountLockout(max_attempts=5, lockout_duration_minutes=30)


async def check_account_lockout(email: str, ip_address: str) -> tuple[bool, Optional[datetime]]:
    """Check if account is locked and record attempt."""
    is_locked, lockout_until = lockout_manager.is_locked(email)

    if is_locked:
        logger.warning(
            "login_attempt_locked", email=email, ip_address=ip_address, lockout_until=lockout_until
        )

    return is_locked, lockout_until


async def record_login_attempt(email: str, ip_address: str, success: bool) -> dict:
    """Record a login attempt."""
    return lockout_manager.record_attempt(email, ip_address, success)


async def unlock_account(email: str) -> None:
    """Unlock an account."""
    lockout_manager.unlock(email)
    logger.info("account_unlocked", email=email)
