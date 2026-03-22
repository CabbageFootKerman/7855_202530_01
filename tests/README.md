# Tests

This folder contains automated tests for the Flask application.

## Purpose

The tests in this folder verify authentication behavior without depending on live Firebase services. They are intended to support local development, CI checks, and live pytest demos in the terminal.

## Current coverage

### Authentication
`test_auth.py` covers the login endpoint in the authentication blueprint.

Tested cases include:

- successful login with a valid Firebase ID token
- missing authentication returning `401 Unauthorized`
- invalid authentication returning `401 Unauthorized`
- bearer-token login flow through the `Authorization` header

## Test structure

### `conftest.py`
Provides shared pytest fixtures for the test suite, including:

- a minimal Flask app configured for testing
- registration of the authentication blueprint
- a Flask test client
- disabled rate limiting during tests

### `test_auth.py`
Contains route-level tests for `/login`.

These tests mock:

- `firebase_admin.auth.verify_id_token`

This allows the login flow to be tested deterministically without making real Firebase calls.

## Running the tests

Run the auth tests with:

```bash
pytest tests/test_auth.py -v

## Rate limiter warning in tests

During local pytest runs and CI, Flask-Limiter may show a warning stating that it is using in-memory storage for rate-limit tracking.

This is acceptable for the current stage of development because the warning appears in the test environment, not because the authentication feature is failing. The tests still run correctly, and this does not block merging the auth work into the main branch.

### Why it happens
The test environment does not currently define a dedicated storage backend for Flask-Limiter, so it falls back to in-memory storage.

### Why it is fine for now
In-memory storage is acceptable for:
- local development
- automated test runs
- short-lived CI environments

### When it should be changed
This should be updated before any serious deployment or shared production use of the app, especially if:
- the app may restart regularly
- multiple workers or instances are used
- rate limiting is expected to be reliable across sessions and deployments

### What should be used later
For production, Flask-Limiter should be configured with a persistent/shared backend such as Redis instead of in-memory storage.

### Current status
No immediate action is required for this assignment task. The warning is informational and does not prevent the login/signup authentication features or their automated tests from functioning correctly.