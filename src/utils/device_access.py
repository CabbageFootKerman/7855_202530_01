import time
import itertools
from threading import Lock

from firebase import db
from firebase_admin import firestore

# ---------------------------------------------------------------------------
# Simple in-process TTL cache for device documents.
# Avoids a Firestore read on every state-poll access-check (which runs every
# few seconds).  Cache entries expire after _DEVICE_CACHE_TTL seconds so
# ownership/permission changes still propagate in a reasonable time.
# time.monotonic() is used for expiry comparisons because it is immune to
# system clock adjustments; the TTL is expressed in relative seconds so
# monotonic time is the correct choice here.
# ---------------------------------------------------------------------------
_DEVICE_CACHE_TTL = 60  # seconds
_device_cache: dict = {}  # device_id -> (data_or_None, expiry_timestamp)
_device_cache_lock = Lock()


def _invalidate_device_cache(device_id: str) -> None:
    with _device_cache_lock:
        _device_cache.pop(device_id, None)


def get_device(device_id):
    now = time.monotonic()
    with _device_cache_lock:
        cached = _device_cache.get(device_id)
        if cached is not None:
            data, expiry = cached
            if now < expiry:
                return data

    doc = db.collection("devices").document(device_id).get()
    if not doc.exists:
        result = None
    else:
        result = doc.to_dict() or {}
        result["id"] = doc.id

    with _device_cache_lock:
        _device_cache[device_id] = (result, now + _DEVICE_CACHE_TTL)
    return result


def get_user_devices(username):
    # Use two targeted index-backed queries instead of a full collection scan.
    owner_docs = db.collection("devices").where("owner_username", "==", username).stream()
    allowed_docs = db.collection("devices").where("allowed_users", "array_contains", username).stream()

    seen: set = set()
    devices = []
    for doc in itertools.chain(owner_docs, allowed_docs):
        if doc.id in seen:
            continue
        seen.add(doc.id)
        data = doc.to_dict() or {}
        data["id"] = doc.id
        devices.append(data)

    return devices


def user_is_device_owner(username, device_id):
    device = get_device(device_id)
    if not device:
        return False
    return device.get("owner_username") == username


def user_can_access_device(username, device_id):
    device = get_device(device_id)
    if not device:
        return False

    if device.get("owner_username") == username:
        return True

    allowed = device.get("allowed_users", [])
    return username in allowed


def claim_device(username, device_id, claim_code):
    ref = db.collection("devices").document(device_id)
    doc = ref.get()

    if not doc.exists:
        return False, "Device not found."

    data = doc.to_dict() or {}

    if data.get("owner_username"):
        return False, "Device already claimed."

    if data.get("claim_code") != claim_code:
        return False, "Invalid claim code."

    ref.update({
        "owner_username": username,
        "allowed_users": [],
        "paired_at": firestore.SERVER_TIMESTAMP,
        "is_claimed": True
    })
    _invalidate_device_cache(device_id)
    return True, "Device claimed."


def add_allowed_user(owner_username, device_id, target_username):
    ref = db.collection("devices").document(device_id)
    doc = ref.get()

    if not doc.exists:
        return False, "Device not found."

    data = doc.to_dict() or {}

    if data.get("owner_username") != owner_username:
        return False, "Only the owner can add users."

    if not target_username:
        return False, "Target username is required."

    if target_username == owner_username:
        return False, "Owner already has access."

    ref.update({
        "allowed_users": firestore.ArrayUnion([target_username])
    })
    _invalidate_device_cache(device_id)
    return True, "User added."


def remove_allowed_user(owner_username, device_id, target_username):
    ref = db.collection("devices").document(device_id)
    doc = ref.get()

    if not doc.exists:
        return False, "Device not found."

    data = doc.to_dict() or {}

    if data.get("owner_username") != owner_username:
        return False, "Only the owner can remove users."

    if not target_username:
        return False, "Target username is required."

    ref.update({
        "allowed_users": firestore.ArrayRemove([target_username])
    })
    _invalidate_device_cache(device_id)
    return True, "User removed."
