"""Thread-safe in-memory caches for notification lists, unread counts, and
door-close chart data.

These caches sit between the API endpoints and Firestore, serving repeated
polling reads from memory and only falling back to Firestore on a cache miss
or after the TTL expires.  All write operations (mark read, clear, new
notification delivered) must call the appropriate invalidation function so
the cache stays coherent.
"""

import time
from threading import Lock

# ---------------------------------------------------------------------------
# Notification list cache (per user)
# Populated when /api/notifications is called; cleared on any write.
# We always cache the full list (up to 100 items, the API max) so that both
# filtered (unread_only) and paginated (limit) variants are served from memory.
# ---------------------------------------------------------------------------

_NOTIF_LIST_TTL = 30  # seconds

_notif_list_cache: dict = {}  # username -> (items: list[dict], expiry: float)
_notif_list_lock = Lock()


def get_cached_notification_list(username: str):
    """Return cached notification list (list of dicts) or None if expired/missing."""
    with _notif_list_lock:
        entry = _notif_list_cache.get(username)
        if entry is not None:
            items, expiry = entry
            if time.monotonic() < expiry:
                return items
    return None


def set_notification_list_cache(username: str, items: list) -> None:
    with _notif_list_lock:
        _notif_list_cache[username] = (items, time.monotonic() + _NOTIF_LIST_TTL)


# ---------------------------------------------------------------------------
# Unread count cache (per user)
# Populated when /api/notifications/unread-count is called; cleared on writes.
# ---------------------------------------------------------------------------

_NOTIF_COUNT_TTL = 60  # seconds – comfortably above the 30-s poll interval

_notif_count_cache: dict = {}  # username -> (count: int, expiry: float)
_notif_count_lock = Lock()


def get_cached_unread_count(username: str):
    """Return cached unread count (int) or None if expired/missing."""
    with _notif_count_lock:
        entry = _notif_count_cache.get(username)
        if entry is not None:
            count, expiry = entry
            if time.monotonic() < expiry:
                return count
    return None


def set_unread_count_cache(username: str, count: int) -> None:
    with _notif_count_lock:
        _notif_count_cache[username] = (count, time.monotonic() + _NOTIF_COUNT_TTL)


def invalidate_notification_cache(username: str) -> None:
    """Clear all cached notification data for a user (list + unread count)."""
    with _notif_list_lock:
        _notif_list_cache.pop(username, None)
    with _notif_count_lock:
        _notif_count_cache.pop(username, None)


# ---------------------------------------------------------------------------
# Door-close chart cache (per device + hours window)
# Populated on /api/device/<device_id>/door-close-chart; TTL-based only.
# A 5-minute TTL is acceptable staleness for an hourly chart that the browser
# refreshes every 60 seconds.
# ---------------------------------------------------------------------------

_CHART_TTL = 300  # 5 minutes

_chart_cache: dict = {}  # (device_id, hours) -> (data: dict, expiry: float)
_chart_lock = Lock()


def get_cached_chart(device_id: str, hours: int):
    """Return cached door-close chart payload or None if expired/missing."""
    with _chart_lock:
        entry = _chart_cache.get((device_id, hours))
        if entry is not None:
            data, expiry = entry
            if time.monotonic() < expiry:
                return data
    return None


def set_chart_cache(device_id: str, hours: int, data: dict) -> None:
    with _chart_lock:
        _chart_cache[(device_id, hours)] = (data, time.monotonic() + _CHART_TTL)
