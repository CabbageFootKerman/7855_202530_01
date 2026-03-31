from unittest.mock import MagicMock, patch


def make_snapshot(*, exists=True, doc_id="alice", data=None):
    snap = MagicMock()
    snap.exists = exists
    snap.id = doc_id
    snap.to_dict.return_value = data or {
        "first_name": "Alice",
        "last_name": "Smith",
        "student_id": "12345678",
    }
    return snap


def test_create_profile_success(client):
    payload = {
        "username": "alice",
        "first_name": "Alice",
        "last_name": "Smith",
        "student_id": "12345678",
    }

    with patch("blueprints.profile.routes.db") as mock_db:
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()

        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref

        response = client.post("/api/profile", json=payload)

    assert response.status_code == 201
    assert response.get_json() == {
        "message": "Created",
        "username": "alice",
    }
    mock_db.collection.assert_called_with("profiles")
    mock_collection.document.assert_called_with("alice")
    mock_doc_ref.set.assert_called_once_with(payload)


def test_create_profile_missing_username_returns_400(client):
    payload = {
        "first_name": "Alice",
        "last_name": "Smith",
    }

    with patch("blueprints.profile.routes.db") as mock_db:
        response = client.post("/api/profile", json=payload)

    assert response.status_code == 400
    assert response.get_json() == {"error": "username is required"}
    mock_db.collection.assert_not_called()


def test_get_profile_success(client):
    with patch("blueprints.profile.routes.db") as mock_db:
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_snapshot = make_snapshot(
            exists=True,
            doc_id="alice",
            data={
                "first_name": "Alice",
                "last_name": "Smith",
                "student_id": "12345678",
            },
        )

        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_snapshot

        response = client.get("/api/profile/alice")

    assert response.status_code == 200
    assert response.get_json() == {
        "username": "alice",
        "first_name": "Alice",
        "last_name": "Smith",
        "student_id": "12345678",
    }
    mock_db.collection.assert_called_with("profiles")
    mock_collection.document.assert_called_with("alice")
    mock_doc_ref.get.assert_called_once()


def test_get_profile_not_found_returns_404(client):
    with patch("blueprints.profile.routes.db") as mock_db:
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_snapshot = make_snapshot(exists=False, doc_id="missing-user", data={})

        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_snapshot

        response = client.get("/api/profile/missing-user")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Not found"}


def test_update_profile_success(client):
    payload = {
        "first_name": "Updated",
        "last_name": "User",
    }

    with patch("blueprints.profile.routes.db") as mock_db:
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_snapshot = make_snapshot(exists=True)

        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_snapshot

        response = client.put("/api/profile/alice", json=payload)

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "Updated",
        "username": "alice",
    }
    mock_db.collection.assert_called_with("profiles")
    mock_collection.document.assert_called_with("alice")
    mock_doc_ref.get.assert_called_once()
    mock_doc_ref.update.assert_called_once_with(payload)


def test_update_profile_not_found_returns_404(client):
    with patch("blueprints.profile.routes.db") as mock_db:
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_snapshot = make_snapshot(exists=False, doc_id="missing-user", data={})

        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_snapshot

        response = client.put(
            "/api/profile/missing-user",
            json={"first_name": "Nobody"},
        )

    assert response.status_code == 404
    assert response.get_json() == {"error": "Not found"}
    mock_doc_ref.update.assert_not_called()


def test_update_profile_empty_json_returns_400(client):
    with patch("blueprints.profile.routes.db") as mock_db:
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_snapshot = make_snapshot(exists=True)

        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_snapshot

        response = client.put("/api/profile/alice", json={})

    assert response.status_code == 400
    assert response.get_json() == {"error": "No fields to update"}
    mock_doc_ref.update.assert_not_called()


def test_update_profile_wrong_content_type_returns_415(client):
    with patch("blueprints.profile.routes.db"):
        response = client.put(
            "/api/profile/alice",
            data="first_name=Alice",
            headers={"Content-Type": "text/plain"},
        )

    assert response.status_code == 415
    assert response.get_json() == {
        "error": "Content-Type must be application/json."
    }


def test_delete_profile_success(client):
    with patch("blueprints.profile.routes.db") as mock_db:
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_snapshot = make_snapshot(exists=True)

        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_snapshot

        response = client.delete("/api/profile/alice")

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "Deleted",
        "username": "alice",
    }
    mock_db.collection.assert_called_with("profiles")
    mock_collection.document.assert_called_with("alice")
    mock_doc_ref.get.assert_called_once()
    mock_doc_ref.delete.assert_called_once()


def test_delete_profile_not_found_returns_404(client):
    with patch("blueprints.profile.routes.db") as mock_db:
        mock_collection = MagicMock()
        mock_doc_ref = MagicMock()
        mock_snapshot = make_snapshot(exists=False, doc_id="missing-user", data={})

        mock_db.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value = mock_snapshot

        response = client.delete("/api/profile/missing-user")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Not found"}
    mock_doc_ref.delete.assert_not_called()