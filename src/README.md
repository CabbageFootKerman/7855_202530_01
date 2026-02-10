# **Code explanations**
---

# Smart Post — Landing Page (UI Entry Point)

This branch adds a public landing page for the Smart Post Flask app.

## What’s included

### Landing page
- **Route:** `GET /`
- **Behavior:** When the user is not logged in, `/` renders `landing.html`.
- **Landing page contents:**
  - Large project title
  - **Login** button (links to `/login`)
  - **Create account / Sign up** button (links to `/signup`)
  - Large image/hero area (uses a placeholder image)

> Note: This branch only adds the landing page UI + wiring. Authentication implementation (login/signup behavior, persistence, etc.) is handled elsewhere.

## Files added / changed

- `templates/landing.html`
- `app.py` (updates `/` route to render `landing.html` when logged out)
- `static/landing.jpg` (if required by the landing page hero image)

## Expected existing routes (owned by other work)
The landing page buttons assume these endpoints exist:
- `/login`
- `/signup`

---
# Smart Post — User Persistence (users.json)

This branch builds on the existing landing page branch and adds **user permanence** to the existing login/signup flow by persisting users to a local JSON file.

> Scope note: This branch does **not** change the landing page UI. It only adds persistence for user accounts.

## What’s included

### User persistence (JSON file)
- Users are stored in `users.json` in the app root (same folder as `app.py`).
- Passwords are stored **hashed** (Werkzeug) — no plaintext passwords.
- Supports legacy plaintext entries (if any) by migrating them to hashed format after a successful login.

### Existing behavior preserved
- `GET|POST /login` continues to authenticate and set `session["username"]`.
- `GET|POST /signup` continues to create users and log them in.
- Landing page behavior remains the same as the parent branch:
  - Logged out: `/` renders `landing.html`
  - Logged in: `/` redirects to `/device/demo123`

## Files changed

- `app.py`
  - Adds `users.json` load/save helpers
  - Updates `/login` to verify hashed passwords
  - Updates `/signup` to save new users to `users.json`

## Runtime-generated files (do NOT commit)

This feature generates a user data file at runtime:
- `users.json`
- `users.tmp` (temporary file used during safe-save)

Add the following to `.gitignore` in main:

```gitignore
users.json
*.tmp
