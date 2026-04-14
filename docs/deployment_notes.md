# Deployment Notes

## Overview
This document records the deployment attempt for the SmartPost application
as part of the COMP 7855 Sprint 4 deliverable.

## Attempted Deployment Steps

1. Created `Dockerfile` with pinned Python 3.11-slim base image
2. Created `docker-compose.yml` wiring app and Redis services
3. Created `.dockerignore` to exclude secrets, venv, and runtime artifacts
4. Added `RATELIMIT_STORAGE_URL=redis://redis:6379` to `.env` for container networking
5. Fixed `config.py` to load `.env` from project root instead of `src/`
6. Ran `docker-compose up --build` — both containers started successfully
7. Confirmed app served pages at `http://localhost:5000`

## Result
✅ Local Docker deployment successful. Both the Flask app and Redis containers
started cleanly. All environment variables confirmed loaded. App served pages
as expected.

## Platform Notes
- Tested on Windows 11 with Docker Desktop
- Docker engine: Linux containers mode
- No deployment blockers encountered locally

## Outstanding Items
- Cloud deployment (e.g. Render, Railway, or similar) not yet attempted
- `serviceAccountKey.json` must be supplied at runtime and must not be baked
  into the image — currently handled via volume mount in `docker-compose.yml`
- `.env` must be present at project root and is excluded from the image via
  `.dockerignore`