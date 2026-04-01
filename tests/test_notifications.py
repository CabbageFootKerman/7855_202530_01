from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch


def set_logged_in(client, username="test_user_123"):
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = username


def make_doc(*, doc_id="doc-1", data=None, exists=True):
    doc = MagicMock()
    doc.id = doc_id
    doc.exists = exists
    doc.reference = MagicMock(name=f"ref_{doc_id}")
    doc.to_dict.return_value = data or {}
    return doc


def test_notifications_list_success(client):
    set_logged_in(client)

    docs = [make_doc(doc_id="n1"), make_doc(doc_id="n2")]

    with patch("blueprints.notifications.routes.db") as mock_db, \
         patch(
             "blueprints.notifications.routes._serialize_doc",
             side_effect=[
                 {"id": "n1", "title": "First"},
                 {"id": "n2", "title": "Second"},
             ],
         ):
        notifications = (
            mock_db.collection.return_value
            .document.return_value
            .collection.return_value
        )
        ordered = MagicMock()
        limited = MagicMock()

        notifications.order_by.return_value = ordered
        ordered.limit.return_value = limited
        limited.stream.return_value = docs

        response = client.get("/api/notifications")

    assert response.status_code == 200
    body = response.get_json()
    assert body["username"] == "test_user_123"
    assert body["count"] == 2
    assert body["items"] == [
        {"id": "n1", "title": "First"},
        {"id": "n2", "title": "Second"},
    ]


def test_notifications_list_invalid_limit_returns_400(client):
    set_logged_in(client)

    response = client.get("/api/notifications?limit=abc")

    assert response.status_code == 400
    assert response.get_json() == {"error": "limit must be an integer"}


def test_notifications_list_unread_only_filters_and_clamps_limit(client):
    set_logged_in(client)

    docs = [make_doc(doc_id="n1")]

    with patch("blueprints.notifications.routes.db") as mock_db, \
         patch(
             "blueprints.notifications.routes._serialize_doc",
             return_value={"id": "n1", "read": False},
         ):
        notifications = (
            mock_db.collection.return_value
            .document.return_value
            .collection.return_value
        )
        filtered = MagicMock()
        ordered = MagicMock()
        limited = MagicMock()

        notifications.where.return_value = filtered
        filtered.order_by.return_value = ordered
        ordered.limit.return_value = limited
        limited.stream.return_value = docs

        response = client.get("/api/notifications?unread_only=true&limit=500")

    assert response.status_code == 200
    notifications.where.assert_called_once_with("read", "==", False)
    ordered.limit.assert_called_once_with(100)
    assert response.get_json()["count"] == 1


def test_notifications_unread_count_success(client):
    set_logged_in(client)

    with patch("blueprints.notifications.routes.db") as mock_db:
        notifications = (
            mock_db.collection.return_value
            .document.return_value
            .collection.return_value
        )
        filtered = notifications.where.return_value
        filtered.stream.return_value = [make_doc(), make_doc(), make_doc()]

        response = client.get("/api/notifications/unread-count")

    assert response.status_code == 200
    assert response.get_json() == {
        "username": "test_user_123",
        "unread_count": 3,
    }


def test_notifications_mark_read_not_found_returns_404(client):
    set_logged_in(client)

    with patch("blueprints.notifications.routes.db") as mock_db:
        doc_ref = (
            mock_db.collection.return_value
            .document.return_value
            .collection.return_value
            .document.return_value
        )
        doc_ref.get.return_value = make_doc(exists=False)

        response = client.post("/api/notifications/notif-123/read")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Notification not found"}


def test_notifications_mark_read_success(client):
    set_logged_in(client)

    with patch("blueprints.notifications.routes.db") as mock_db:
        doc_ref = (
            mock_db.collection.return_value
            .document.return_value
            .collection.return_value
            .document.return_value
        )
        doc_ref.get.return_value = make_doc(doc_id="notif-123", exists=True)

        response = client.post("/api/notifications/notif-123/read")

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "Marked as read",
        "notification_id": "notif-123",
    }

    payload = doc_ref.update.call_args[0][0]
    assert payload["read"] is True
    assert "read_at" in payload
    assert "updated_at" in payload


def test_notifications_mark_all_read_success(client):
    set_logged_in(client)

    docs = [make_doc(doc_id="a"), make_doc(doc_id="b")]
    batch = MagicMock()

    with patch("blueprints.notifications.routes.db") as mock_db:
        notifications = (
            mock_db.collection.return_value
            .document.return_value
            .collection.return_value
        )
        filtered = notifications.where.return_value
        filtered.stream.return_value = docs
        mock_db.batch.return_value = batch

        response = client.post("/api/notifications/read-all")

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "Marked all as read",
        "updated_count": 2,
    }
    assert batch.update.call_count == 2
    batch.commit.assert_called_once()


def test_notifications_mark_all_read_with_no_unread(client):
    set_logged_in(client)

    batch = MagicMock()

    with patch("blueprints.notifications.routes.db") as mock_db:
        notifications = (
            mock_db.collection.return_value
            .document.return_value
            .collection.return_value
        )
        filtered = notifications.where.return_value
        filtered.stream.return_value = []
        mock_db.batch.return_value = batch

        response = client.post("/api/notifications/read-all")

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "Marked all as read",
        "updated_count": 0,
    }
    batch.commit.assert_not_called()


def test_notifications_clear_invalid_mode_returns_400(client):
    set_logged_in(client)

    response = client.post("/api/notifications/clear", json={"mode": "bad-mode"})

    assert response.status_code == 400
    assert response.get_json() == {"error": "mode must be 'all' or 'read'"}


def test_notifications_clear_read_when_nothing_to_clear(client):
    set_logged_in(client)

    with patch("blueprints.notifications.routes.db") as mock_db:
        notifications = (
            mock_db.collection.return_value
            .document.return_value
            .collection.return_value
        )
        filtered = notifications.where.return_value
        filtered.stream.return_value = []

        response = client.post("/api/notifications/clear", json={"mode": "read"})

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "Nothing to clear",
        "cleared_count": 0,
        "mode": "read",
    }


def test_notifications_clear_all_success(client):
    set_logged_in(client)

    docs = [make_doc(doc_id="x"), make_doc(doc_id="y")]
    batch = MagicMock()

    with patch("blueprints.notifications.routes.db") as mock_db:
        notifications = (
            mock_db.collection.return_value
            .document.return_value
            .collection.return_value
        )
        notifications.stream.return_value = docs
        mock_db.batch.return_value = batch

        response = client.post("/api/notifications/clear", json={"mode": "all"})

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "Notifications cleared",
        "cleared_count": 2,
        "mode": "all",
    }
    assert batch.delete.call_count == 2
    batch.commit.assert_called_once()


def test_demo_notify_invalid_preset_returns_400(client):
    set_logged_in(client)

    response = client.post(
        "/api/device/device-001/demo-notify",
        json={"preset": "not-real"},
    )

    assert response.status_code == 400
    body = response.get_json()
    assert body["error"] == "Invalid preset"
    assert "package_detected" in body["valid_presets"]


def test_demo_notify_success(client):
    set_logged_in(client)

    fake_result = {"id": "notif-1", "title": "Package detected"}

    with patch(
        "blueprints.notifications.routes.publish_device_notification",
        return_value=fake_result,
    ) as mock_publish:
        response = client.post(
            "/api/device/device-001/demo-notify",
            json={"preset": "package_detected"},
        )

    assert response.status_code == 200
    body = response.get_json()
    assert body["message"] == "Demo notification generated"
    assert body["preset"] == "package_detected"
    assert body["notification"] == fake_result

    mock_publish.assert_called_once_with(
        actor_username="test_user_123",
        device_id="device-001",
        notif_type="package_detected",
        title="Package detected",
        body="Device device-001 detected a package.",
        severity="success",
        data={"source": "demo", "event": "package_detected"},
    )


def test_door_close_chart_forbidden_returns_403(client):
    set_logged_in(client)

    with patch(
        "blueprints.notifications.routes.user_can_access_device",
        return_value=False,
    ):
        response = client.get("/api/device/device-001/door-close-chart")

    assert response.status_code == 403
    assert response.get_json() == {"error": "Forbidden"}


def test_door_close_chart_invalid_hours_returns_400(client):
    set_logged_in(client)

    with patch(
        "blueprints.notifications.routes.user_can_access_device",
        return_value=True,
    ):
        response = client.get("/api/device/device-001/door-close-chart?hours=abc")

    assert response.status_code == 400
    assert response.get_json() == {"error": "hours must be an integer"}


def test_door_close_chart_success_counts_supported_events(client):
    set_logged_in(client)

    now = datetime.now(timezone.utc)

    docs = [
        make_doc(
            doc_id="e1",
            data={
                "type": "door_closed",
                "logged_at": now - timedelta(minutes=10),
            },
        ),
        make_doc(
            doc_id="e2",
            data={
                "type": "door_close_requested",
                "created_at_client_iso": (
                    now - timedelta(hours=1, minutes=5)
                ).isoformat().replace("+00:00", "Z"),
            },
        ),
        make_doc(
            doc_id="e3",
            data={
                "type": "door_closed",
                "logged_at": (now - timedelta(minutes=5)).replace(tzinfo=None),
            },
        ),
        make_doc(
            doc_id="e4",
            data={
                "type": "other_event",
                "logged_at": now - timedelta(minutes=5),
            },
        ),
        make_doc(
            doc_id="e5",
            data={
                "type": "door_closed",
                "created_at_client_iso": "not-a-date",
            },
        ),
        make_doc(
            doc_id="e6",
            data={
                "type": "door_close_requested",
                "logged_at": now - timedelta(days=10),
            },
        ),
    ]

    with patch(
        "blueprints.notifications.routes.user_can_access_device",
        return_value=True,
    ), patch("blueprints.notifications.routes.db") as mock_db:
        query = mock_db.collection.return_value.where.return_value
        query.stream.return_value = docs

        response = client.get("/api/device/device-001/door-close-chart?hours=24")

    assert response.status_code == 200
    body = response.get_json()

    assert body["device_id"] == "device-001"
    assert len(body["labels"]) == 24
    assert len(body["values"]) == 24
    assert sum(body["values"]) == 3
    assert body["total"] == 3