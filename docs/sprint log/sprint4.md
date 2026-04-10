# Sprint 4 Plan

## Team
- SmartPost WAN Robot Control
- Mikhail Rego
- Pawel Banasik
- Glen Healy
- Ryan McKay

## Sprint 4 Goal
Make the system portable, automated, documented, and demo-ready. Sprint 4 is not for new features. The focus is Docker, CI, deployment, logging, handoff documentation, and demo preparation.

## Non-Negotiables
- Feature freeze: no new endpoints, pages, charts, or libraries.
- Finish any pytest carry-over first because CI depends on it.
- Only one person edits a given file this sprint.
- All Sprint 3 work must be merged into `main` before final handoff.

## Overall Backlog
1. Finish pytest carry-over and ensure Firestore is fully mocked.
2. Dockerize the app so a new developer can run it with one command.
3. Replace `print()` usage with structured logging.
4. Add GitHub Actions CI for pushes and PRs to `main`.
5. Deploy the Dockerized app to a public HTTPS URL.
6. Finalize README handoff docs, `.env.example`, and Sprint 4 documentation.
7. Prepare demo plan, backup video, and final report.

## File Ownership Plan

### Mikhail Rego
Scope: planning, documentation, coordination.

**Modify**
- `README.md`
- `docs/sprint log/sprint4.md`

**Create**
- `.env.example`
- `docs/final_report.md`
- `docs/demo_plan.md`

**Do Not Touch**
- `src/**`
- `tests/**`
- `Dockerfile`
- `docker-compose.yml`
- `.github/workflows/ci.yml`

### Ryan Mckay
Scope: pytest carry-over, mocking, CI reliability.

**Modify**
- `tests/conftest.py`
- `tests/test_auth.py`
- `tests/test_device.py`
- `tests/test_notifications.py`
- `tests/test_profile.py`
- `pytest.ini`
- `.github/workflows/ci.yml`

**Create**
- `tests/test_media.py` if media coverage is added

**Do Not Touch**
- `src/**`
- `README.md`
- `Dockerfile`
- `docker-compose.yml`

### Pawel Banasik
Scope: Docker setup, cloud deployment, operational portability.

**Modify**
- `requirements.txt` only if a deployment/runtime package is strictly required

**Create**
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `docs/deployment_notes.md` if deployment is blocked or needs explanation

**Do Not Touch**
- `src/**`
- `tests/**`
- `README.md`
- `.github/workflows/ci.yml`

### Glen Healy
Scope: structured logging and final runtime cleanup inside the app.

**Modify**
- `src/app.py`
- `src/blueprints/auth/routes.py`
- `src/blueprints/device/routes.py`
- `src/blueprints/notifications/routes.py`
- `src/extensions.py` only if needed for logging initialization

**Create**
- `src/logging_config.py` only if central logging setup is needed

**Remove**
- `print()`-based startup or request debugging where replaced by logging

**Do Not Touch**
- `README.md`
- `tests/**`
- `Dockerfile`
- `docker-compose.yml`
- `.github/workflows/ci.yml`

## Definition of Done
- `docker-compose up --build` starts the app successfully.
- Logs show timestamps and severity in Docker output.
- GitHub Actions passes on `main`.
- Firestore is mocked in tests; no production calls in CI.
- A public HTTPS deployment is reachable, or `docs/deployment_notes.md` clearly explains the blocker.
- `README.md` contains architecture, quickstart, API table, and handoff information.
- Demo plan, backup video plan, and final report draft are assigned.

## Demo and Handoff Work
- Mikhail: presentation structure, speaking order, final report draft, Sprint 4 log.
- Glen: deployed URL, deployment proof, Docker demo readiness.
- Ryan: passing tests and CI proof.
- Pawel: application logging demo, auth/error-handling walkthrough.

## Coordination Rule
If a task requires edits to a file owned by another person, do not edit it. Open a PR comment or coordinate a handoff first.