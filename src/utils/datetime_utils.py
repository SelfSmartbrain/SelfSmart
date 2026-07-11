"""
Timezone-aware datetime utilities.

Replaces deprecated datetime.utcnow() with timezone-aware alternatives.
All datetimes returned are timezone-aware (UTC) to prevent
TypeError when comparing with other timezone-aware datetimes.
"""

from datetime import datetime, timezone
from typing import Optional


def utcnow() -> datetime:
    """
    Get current UTC time as timezone-aware datetime.
    
    Replaces deprecated datetime.utcnow() which returns naive datetime.
    
    Returns:
        Current UTC time with timezone info (timezone.utc)
    """
    return datetime.now(timezone.utc)


def utcnow_isoformat() -> str:
    """
    Get current UTC time as ISO format string.
    
    Returns:
        ISO 8601 formatted UTC timestamp with timezone (e.g., '2024-01-15T10:30:00+00:00')
    """
    return utcnow().isoformat()


def utcnow_naive_utc() -> datetime:
    """
    Get current UTC time as naive datetime (UTC but no timezone info).
    
    Use ONLY when interfacing with legacy code or databases that require
    naive UTC datetimes. Prefer utcnow() for new code.
    """
    return datetime.utcnow()


def parse_isoformat(dt_string: str) -> datetime:
    """
    Parse ISO format datetime string, ensuring result is timezone-aware.
    
    Args:
        dt_string: ISO 8601 datetime string
        
    Returns:
        Timezone-aware datetime (UTC if no timezone specified)
    """
    dt = datetime.fromisoformat(dt_string)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def ensure_utc(dt: datetime) -> datetime:
    """
    Ensure a datetime is timezone-aware in UTC.
    
    Args:
        dt: A datetime (naive or timezone-aware)
        
    Returns:
        Timezone-aware datetime in UTC
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def age_days(created_at: datetime) -> int:
    """
    Calculate age in days from a timestamp to now.
    
    Handles both naive and timezone-aware datetimes safely.
    
    Args:
        created_at: The creation timestamp
        
    Returns:
        Number of full days elapsed
    """
    now = utcnow()
    created = ensure_utc(created_at)
    return (now - created).days