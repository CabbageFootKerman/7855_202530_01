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
