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