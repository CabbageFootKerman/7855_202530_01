from datetime import datetime, timezone


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_fs_dt(dt: datetime) -> datetime:
    """Firestore timestamps sometimes come back naive; treat naive as UTC."""
    if isinstance(dt, datetime) and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _serialize_firestore_value(value):
    """Convert Firestore/python values into JSON-safe forms for API responses."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _serialize_firestore_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize_firestore_value(v) for v in value]
    return value


def _serialize_doc(doc) -> dict:
    data = doc.to_dict() or {}
    data = _serialize_firestore_value(data)
    data["id"] = doc.id
    return data
