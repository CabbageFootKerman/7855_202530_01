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


def _clear_project_modules():
    prefixes = (
        "app",
        "blueprints",
        "decorators",
        "utils",
        "extensions",
    )

    for name in list(sys.modules):
        if name == "app" or name.startswith(prefixes):
            sys.modules.pop(name, None)


@pytest.fixture#(scope="session")
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

"""
@pytest.fixture#(scope="session")
def app_module(force_test_env, mock_firestore, mock_redis):
    ""
    Import the Flask app once for the whole test session.
    This is the main fix for the repeated reimport cost.
    ""
    mp = pytest.MonkeyPatch()

    mp.setenv("SENSOR_API_KEY", "test-sensor-key")
    mp.setenv("SMARTPOST_PI_API_KEY", "test-sensor-key")
    mp.setitem(sys.modules, "firebase", mock_firestore["module"])
    mp.setenv("RATELIMIT_STORAGE_URI", "memory://")

    _clear_project_modules()
    app_module = importlib.import_module("app")

    app_module.app.config.update(
        TESTING=True,
        RATELIMIT_ENABLED=False,
        SECRET_KEY="test-secret-key",
        RATELIMIT_STORAGE_URI="memory://",
        CACHE_TYPE="SimpleCache",   # if Flask-Caching is used)
    )

    yield app_module
    _clear_project_modules()
    mp.undo()
"""
@pytest.fixture
def app_module(force_test_env, monkeypatch, mock_firestore, mock_redis):
    monkeypatch.setitem(sys.modules, "firebase", mock_firestore["module"])
    monkeypatch.setenv("RATELIMIT_STORAGE_URI", "memory://")

    _clear_project_modules()
    app_module = importlib.import_module("app")

    app_module.app.config.update(
        TESTING=True,
        RATELIMIT_ENABLED=False,
        SECRET_KEY="test-secret-key",
        RATELIMIT_STORAGE_URI="memory://",
        CACHE_TYPE="SimpleCache",
        SENSOR_API_KEY="test-sensor-key",
        SMARTPOST_PI_API_KEY="test-sensor-key",
    )

    import utils.auth as auth_utils
    monkeypatch.setattr(auth_utils, "SENSOR_API_KEY", "test-sensor-key", raising=False)
    monkeypatch.setattr(auth_utils, "SMARTPOST_PI_API_KEY", "test-sensor-key", raising=False)

    yield app_module
    _clear_project_modules()


@pytest.fixture
def client(app_module):
    """
    Fresh client per test, but no app reimport per test.
    Keeps cookies/session isolated while staying fast.
    """
    #monkeypatch.setattr("utils.auth.SENSOR_API_KEY", "test-sensor-key", raising=False)

    with app_module.app.test_client() as test_client:
        yield test_client


@pytest.fixture
def mock_firebase_auth(monkeypatch):
    """Patch JWT verification to return a known test uid by default."""
    verify_mock = MagicMock(return_value={"uid": "test_user_123"})
    monkeypatch.setattr("decorators.auth.auth.verify_id_token", verify_mock)
    return verify_mock

    """
@pytest.fixture(autouse=True)
def force_test_device_key(monkeypatch):
    monkeypatch.setattr("utils.auth.SENSOR_API_KEY", "test-sensor-key", raising=False)
    monkeypatch.setenv("SMARTPOST_PI_API_KEY", "test-sensor-key")
    """
    
@pytest.fixture(autouse=True)
def disable_all_rate_limits(app_module, monkeypatch):
    import extensions
    monkeypatch.setattr(extensions.limiter, "enabled", False, raising=False)
    

@pytest.fixture(autouse=True)
def clear_in_memory_caches(app_module):
    """Reset all in-process caches before every test so tests are isolated."""
    import utils.notification_cache as nc
    import utils.device_access as da

    def _clear():
        with nc._notif_list_lock:
            nc._notif_list_cache.clear()
        with nc._notif_count_lock:
            nc._notif_count_cache.clear()
        with nc._chart_lock:
            nc._chart_cache.clear()
        with da._device_cache_lock:
            da._device_cache.clear()
        with da._user_devices_lock:
            da._user_devices_cache.clear()

    _clear()  # Clear any other caches if needed
    yield
    _clear()


@pytest.fixture(autouse=True)
def force_test_env(monkeypatch):
    monkeypatch.setenv("SENSOR_API_KEY", "test-sensor-key")
    monkeypatch.setenv("SMARTPOST_PI_API_KEY", "test-sensor-key")

    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("FIREBASE_CONFIG", raising=False)
    monkeypatch.delenv("FIRESTORE_EMULATOR_HOST", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    monkeypatch.delenv("GCLOUD_PROJECT", raising=False)

    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("CACHE_REDIS_URL", raising=False)


@pytest.fixture
def mock_redis(monkeypatch):
    fake_redis = MagicMock(name="fake_redis")

    monkeypatch.setattr("redis.Redis", MagicMock(return_value=fake_redis), raising=False)
    monkeypatch.setattr("redis.StrictRedis", MagicMock(return_value=fake_redis), raising=False)
    monkeypatch.setattr("redis.from_url", MagicMock(return_value=fake_redis), raising=False)

    return fake_redis