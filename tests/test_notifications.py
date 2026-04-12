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
        # The endpoint always fetches up to 100 to populate the cache.
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
    # Confirm the endpoint always fetches 100 from Firestore to maximise cache hits.
    ordered.limit.assert_called_once_with(100)


def test_notifications_list_invalid_limit_returns_400(client):
    set_logged_in(client)

    response = client.get("/api/notifications?limit=abc")

    assert response.status_code == 400
    assert response.get_json() == {"error": "limit must be an integer"}


def test_notifications_list_unread_only_filters_and_clamps_limit(client):
    set_logged_in(client)

    # Provide one unread and one read doc so the in-memory filter is exercised.
    docs = [
        make_doc(doc_id="n1", data={"read": False}),
        make_doc(doc_id="n2", data={"read": True}),
    ]

    with patch("blueprints.notifications.routes.db") as mock_db, \
         patch(
             "blueprints.notifications.routes._serialize_doc",
             side_effect=[
                 {"id": "n1", "read": False},
                 {"id": "n2", "read": True},
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

        response = client.get("/api/notifications?unread_only=true&limit=500")

    assert response.status_code == 200
    body = response.get_json()
    # Only the unread item should appear; limit is clamped to 100 server-side
    # but there is only 1 unread item in the cache so count == 1.
    assert body["count"] == 1
    assert body["items"] == [{"id": "n1", "read": False}]
    # The endpoint no longer applies .where("read", "==", False) at the Firestore
    # level – it fetches all and filters in memory from the cache.
    assert not notifications.where.called
    # It always fetches 100 from Firestore on a cache miss.
    ordered.limit.assert_called_once_with(100)


def test_notifications_unread_count_success(client):
    set_logged_in(client)

    with patch("blueprints.notifications.routes.db") as mock_db:
        notifications = (
            mock_db.collection.return_value
            .document.return_value
            .collection.return_value
        )
        filtered = notifications.where.return_value

        # Mock the count() aggregation: result[0][0].value == 3
        count_row = MagicMock()
        count_row.value = 3
        filtered.count.return_value.get.return_value = [[count_row]]

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
        # Two chained .where() calls are now used: .where(device_id).where(logged_at)
        query = mock_db.collection.return_value.where.return_value.where.return_value
        query.stream.return_value = docs

        response = client.get("/api/device/device-001/door-close-chart?hours=24")

    assert response.status_code == 200
    body = response.get_json()

    assert body["device_id"] == "device-001"
    assert len(body["labels"]) == 24
    assert len(body["values"]) == 24
    assert sum(body["values"]) == 3
    assert body["total"] == 3


# ---------------------------------------------------------------------------
# Cache-hit and cache-invalidation tests
# ---------------------------------------------------------------------------

def test_unread_count_served_from_cache(client):
    """Second call to unread-count is served from cache (no Firestore query)."""
    set_logged_in(client)

    with patch("blueprints.notifications.routes.db") as mock_db:
        notifications = (
            mock_db.collection.return_value
            .document.return_value
            .collection.return_value
        )
        filtered = notifications.where.return_value
        count_row = MagicMock()
        count_row.value = 5
        filtered.count.return_value.get.return_value = [[count_row]]

        # First request: cache miss → Firestore query
        r1 = client.get("/api/notifications/unread-count")
        assert r1.status_code == 200
        assert r1.get_json()["unread_count"] == 5
        assert filtered.count.call_count == 1

        # Second request: cache hit → no additional Firestore query
        r2 = client.get("/api/notifications/unread-count")
        assert r2.status_code == 200
        assert r2.get_json()["unread_count"] == 5
        assert filtered.count.call_count == 1  # still 1 – cache was used


def test_notification_list_served_from_cache(client):
    """Second call to the notification list is served from cache."""
    set_logged_in(client)

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
        limited = notifications.order_by.return_value.limit.return_value
        limited.stream.return_value = [make_doc(doc_id="n1")]

        r1 = client.get("/api/notifications")
        assert r1.status_code == 200
        assert limited.stream.call_count == 1

        # Second request: cache hit
        r2 = client.get("/api/notifications")
        assert r2.status_code == 200
        assert limited.stream.call_count == 1  # no additional Firestore call


def test_mark_read_invalidates_cache(client):
    """Marking a notification read clears the per-user notification cache."""
    import utils.notification_cache as nc

    set_logged_in(client)

    # Pre-populate the cache with a known value.
    nc.set_unread_count_cache("test_user_123", 3)
    nc.set_notification_list_cache("test_user_123", [{"id": "n1", "read": False}])

    with patch("blueprints.notifications.routes.db") as mock_db:
        doc_ref = (
            mock_db.collection.return_value
            .document.return_value
            .collection.return_value
            .document.return_value
        )
        doc_ref.get.return_value = make_doc(doc_id="n1", exists=True)

        response = client.post("/api/notifications/n1/read")

    assert response.status_code == 200
    # Cache must be cleared so the next poll hits Firestore.
    assert nc.get_cached_unread_count("test_user_123") is None
    assert nc.get_cached_notification_list("test_user_123") is None


def test_mark_all_read_invalidates_cache(client):
    """Marking all notifications read clears the per-user cache."""
    import utils.notification_cache as nc

    set_logged_in(client)

    nc.set_unread_count_cache("test_user_123", 2)

    with patch("blueprints.notifications.routes.db") as mock_db:
        notifications = (
            mock_db.collection.return_value
            .document.return_value
            .collection.return_value
        )
        filtered = notifications.where.return_value
        filtered.stream.return_value = [make_doc(doc_id="a"), make_doc(doc_id="b")]
        mock_db.batch.return_value = MagicMock()

        response = client.post("/api/notifications/read-all")

    assert response.status_code == 200
    assert nc.get_cached_unread_count("test_user_123") is None


def test_clear_notifications_invalidates_cache(client):
    """Clearing notifications removes the user's cache entries."""
    import utils.notification_cache as nc

    set_logged_in(client)

    nc.set_notification_list_cache("test_user_123", [{"id": "x"}, {"id": "y"}])

    with patch("blueprints.notifications.routes.db") as mock_db:
        notifications = (
            mock_db.collection.return_value
            .document.return_value
            .collection.return_value
        )
        filtered = notifications.where.return_value
        filtered.stream.return_value = [make_doc(doc_id="x"), make_doc(doc_id="y")]
        mock_db.batch.return_value = MagicMock()

        response = client.post("/api/notifications/clear", json={"mode": "read"})

    assert response.status_code == 200
    assert nc.get_cached_notification_list("test_user_123") is None


def test_door_close_chart_served_from_cache(client):
    """Second call to door-close-chart is served from cache (no Firestore query)."""
    set_logged_in(client)

    with patch(
        "blueprints.notifications.routes.user_can_access_device",
        return_value=True,
    ), patch("blueprints.notifications.routes.db") as mock_db:
        query = mock_db.collection.return_value.where.return_value.where.return_value
        query.stream.return_value = []

        r1 = client.get("/api/device/device-001/door-close-chart?hours=24")
        assert r1.status_code == 200
        assert query.stream.call_count == 1

        # Second request within TTL: served from cache
        r2 = client.get("/api/device/device-001/door-close-chart?hours=24")
        assert r2.status_code == 200
        assert query.stream.call_count == 1  # no additional Firestore call