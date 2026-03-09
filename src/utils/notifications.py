import uuid
from typing import Any, Dict, List, Optional

from firebase_admin import firestore

from config import NOTIFICATION_SCHEMA_VERSION
from firebase import db
from utils.firestore import _utc_now_iso


# ---------------------------
# Channel interfaces
# ---------------------------

class NotificationChannel:
    """
    Base channel interface.
    Teammates can add WebPushChannel / MobilePushChannel later and register them.
    """
    name = "base"

    def deliver(self, payload: dict, recipients: List[str]) -> dict:
        raise NotImplementedError


class FirestoreEventLogChannel(NotificationChannel):
    """
    Writes a global event log:
      notification_events/{event_id}
    Useful for debugging, auditing, and demoing.
    """
    name = "firestore_event_log"

    def __init__(self, db_client):
        self.db = db_client

    def deliver(self, payload: dict, recipients: List[str]) -> dict:
        event_id = payload["event_id"]
        event_doc = {
            **payload,
            "recipient_usernames": recipients,
            "logged_at": firestore.SERVER_TIMESTAMP,
        }
        self.db.collection("notification_events").document(event_id).set(event_doc)
        return {"channel": self.name, "status": "ok", "logged_event_id": event_id}


class FirestoreUserInboxChannel(NotificationChannel):
    """
    Writes per-user inbox entries:
      users/{username}/notifications/{event_id}
    This is the actual in-app notification store.
    """
    name = "firestore_user_inbox"

    def __init__(self, db_client):
        self.db = db_client

    def deliver(self, payload: dict, recipients: List[str]) -> dict:
        event_id = payload["event_id"]
        writes = 0

        for username in recipients:
            doc_ref = (
                self.db.collection("users")
                .document(username)
                .collection("notifications")
                .document(event_id)
            )

            doc_ref.set({
                **payload,
                "username": username,  # recipient
                "read": False,
                "read_at": None,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
                "delivery": {
                    "in_app": {"status": "delivered", "at_client_iso": _utc_now_iso()},
                    # placeholders for future channels
                    "web_push": {"status": "not_attempted"},
                    "mobile_push": {"status": "not_attempted"},
                },
            }, merge=True)

            writes += 1

        return {"channel": self.name, "status": "ok", "writes": writes}


class StubWebPushChannel(NotificationChannel):
    """
    Placeholder only. Teammates can replace internals with FCM/web push later.
    """
    name = "web_push_stub"

    def deliver(self, payload: dict, recipients: List[str]) -> dict:
        return {
            "channel": self.name,
            "status": "skipped",
            "reason": "stub_not_implemented",
            "recipient_count": len(recipients),
        }


class StubMobilePushChannel(NotificationChannel):
    """
    Placeholder only. Teammates can replace internals with FCM APNs/Android later.
    """
    name = "mobile_push_stub"

    def deliver(self, payload: dict, recipients: List[str]) -> dict:
        return {
            "channel": self.name,
            "status": "skipped",
            "reason": "stub_not_implemented",
            "recipient_count": len(recipients),
        }


# ---------------------------
# Notification service
# ---------------------------

class NotificationService:
    """
    Notification orchestration layer.
    This is the key structural piece: one publish() call fans out to channels.
    """
    def __init__(self, db_client, channels: Optional[List[NotificationChannel]] = None):
        self.db = db_client
        self.channels = channels or []

    def publish(
        self,
        *,
        recipients: List[str],
        notif_type: str,
        title: str,
        body: str,
        severity: str = "info",
        actor_username: Optional[str] = None,
        device_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> dict:
        recipients = [r for r in recipients if r]
        if not recipients:
            return {
                "status": "skipped",
                "reason": "no_recipients",
                "deliveries": [],
            }

        event_id = str(uuid.uuid4())

        payload = {
            "schema_version": NOTIFICATION_SCHEMA_VERSION,
            "event_id": event_id,
            "type": notif_type,
            "title": title,
            "body": body,
            "severity": severity,  # info | warning | error | success
            "actor_username": actor_username,
            "device_id": device_id,
            "data": data or {},
            # client-visible creation time (immediate); Firestore server timestamp is written by channel
            "created_at_client_iso": _utc_now_iso(),
        }

        deliveries = []
        for channel in self.channels:
            try:
                result = channel.deliver(payload, recipients)
                deliveries.append(result)
            except Exception as e:
                deliveries.append({
                    "channel": getattr(channel, "name", "unknown"),
                    "status": "error",
                    "error": str(e),
                })

        return {
            "status": "ok",
            "event_id": event_id,
            "recipient_count": len(recipients),
            "deliveries": deliveries,
        }


# ---------------------------
# Recipient resolver + convenience publisher
# ---------------------------

def resolve_notification_recipients_for_device(
    *,
    device_id: Optional[str],
    actor_username: Optional[str],
) -> List[str]:
    """
    DEMO/TEMP recipient resolver.

    Current behavior:
    - sends notifications to the current logged-in user only.

    Future teammates can replace this with:
    - device owner lookup
    - shared users
    - team roles
    - user preferences / muting
    """
    recipients = []
    if actor_username:
        recipients.append(actor_username)

    # Deduplicate while preserving order
    deduped = []
    seen = set()
    for r in recipients:
        if r not in seen:
            seen.add(r)
            deduped.append(r)
    return deduped


# ---------------------------
# Module-level singleton
# ---------------------------

notification_service = NotificationService(
    db_client=db,
    channels=[
        FirestoreEventLogChannel(db),
        FirestoreUserInboxChannel(db),
        StubWebPushChannel(),    # placeholder
        StubMobilePushChannel(), # placeholder
    ],
)


def publish_device_notification(
    *,
    actor_username: str,
    device_id: str,
    notif_type: str,
    title: str,
    body: str,
    severity: str = "info",
    data: Optional[Dict[str, Any]] = None,
) -> dict:
    recipients = resolve_notification_recipients_for_device(
        device_id=device_id,
        actor_username=actor_username,
    )
    return notification_service.publish(
        recipients=recipients,
        notif_type=notif_type,
        title=title,
        body=body,
        severity=severity,
        actor_username=actor_username,
        device_id=device_id,
        data=data,
    )
