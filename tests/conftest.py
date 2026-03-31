from pathlib import Path
import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def mock_firestore(monkeypatch):
    """Starter Firestore mock fixture.

    This injects a fake `firebase` module before app import so tests do not
    require real Firebase credentials or network access.
    """
    mock_db = MagicMock(name="mock_db")
    mock_collection = MagicMock(name="mock_collection")
    mock_doc_ref = MagicMock(name="mock_doc_ref")
    mock_snapshot = MagicMock(name="mock_snapshot")

    mock_db.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_doc_ref
    mock_doc_ref.get.return_value = mock_snapshot

    mock_snapshot.exists = True
    mock_snapshot.to_dict.return_value = {
        "first_name": "Test",
        "last_name": "User",
        "student_id": "12345678",
    }

    fake_firebase_module = types.ModuleType("firebase")
    fake_firebase_module.db = mock_db
    monkeypatch.setitem(sys.modules, "firebase", fake_firebase_module)

    return {
        "db": mock_db,
        "collection": mock_collection,
        "doc_ref": mock_doc_ref,
        "snapshot": mock_snapshot,
    }


from pathlib import Path
import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(scope="session")
def mock_firestore():
    """One fake firebase/db for the test session."""
    mock_db = MagicMock(name="mock_db")
    mock_collection = MagicMock(name="mock_collection")
    mock_doc_ref = MagicMock(name="mock_doc_ref")
    mock_snapshot = MagicMock(name="mock_snapshot")

    mock_db.collection.return_value = mock_collection
    mock_collection.document.return_value = mock_doc_ref
    mock_doc_ref.get.return_value = mock_snapshot

    mock_snapshot.exists = True
    mock_snapshot.to_dict.return_value = {
        "first_name": "Test",
        "last_name": "User",
        "student_id": "12345678",
    }

    fake_firebase_module = types.ModuleType("firebase")
    fake_firebase_module.db = mock_db

    return {
        "db": mock_db,
        "collection": mock_collection,
        "doc_ref": mock_doc_ref,
        "snapshot": mock_snapshot,
        "module": fake_firebase_module,
    }


@pytest.fixture(scope="session")
def app_module(mock_firestore):
    """
    Import the Flask app once for the whole test session.
    This is the main fix for the repeated reimport cost.
    """
    mp = pytest.MonkeyPatch()

    mp.setenv("SENSOR_API_KEY", "test-sensor-key")
    mp.setenv("SMARTPOST_PI_API_KEY", "test-sensor-key")
    mp.setitem(sys.modules, "firebase", mock_firestore["module"])

    app_module = importlib.import_module("app")
    app_module.app.config.update(
        TESTING=True,
        RATELIMIT_ENABLED=False,
        SECRET_KEY="test-secret-key",
        RATELIMIT_STORAGE_URI="memory://",
    )

    yield app_module
    mp.undo()


@pytest.fixture
def client(app_module, monkeypatch):
    """
    Fresh client per test, but no app reimport per test.
    Keeps cookies/session isolated while staying fast.
    """
    monkeypatch.setattr("utils.auth.SENSOR_API_KEY", "test-sensor-key", raising=False)

    with app_module.app.test_client() as test_client:
        yield test_client


@pytest.fixture
def mock_firebase_auth(monkeypatch):
    """Patch JWT verification to return a known test uid by default."""
    verify_mock = MagicMock(return_value={"uid": "test_user_123"})
    monkeypatch.setattr("decorators.auth.auth.verify_id_token", verify_mock)
    return verify_mock


@pytest.fixture(autouse=True)
def force_test_device_key(monkeypatch):
    monkeypatch.setattr("utils.auth.SENSOR_API_KEY", "test-sensor-key", raising=False)
    monkeypatch.setenv("SMARTPOST_PI_API_KEY", "test-sensor-key")


@pytest.fixture
def mock_firebase_auth(monkeypatch):
    """Patch JWT verification to return a known test uid by default."""
    verify_mock = MagicMock(return_value={"uid": "test_user_123"})
    monkeypatch.setattr("decorators.auth.auth.verify_id_token", verify_mock)
    return verify_mock

@pytest.fixture(autouse=True)
def force_test_device_key(monkeypatch):
    monkeypatch.setattr("utils.auth.SENSOR_API_KEY", "test-sensor-key", raising=False)
    monkeypatch.setenv("SMARTPOST_PI_API_KEY", "test-sensor-key")

@pytest.fixture(autouse=True)
def disable_all_rate_limits():
    import extensions
    extensions.limiter.enabled = False
    yield
    extensions.limiter.enabled = True