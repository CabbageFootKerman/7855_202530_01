# **Code explanations**
---
 

 
# Smart Post � Landing Pages (UI Entry Point)

This branch adds a public landing page for the Smart Post Flask app.

## What�s included

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


## Device Webpage (`device.html`) — Section Explanations

1. **Status Section**
  - Shows the current state of the device: door status (open/closed), weight (g), and last update time.
  - Includes “Open” and “Close” buttons to send commands to the device.
  - Displays command results or errors.

2. **Cameras Section**
  - Displays three camera feeds (or placeholder images if no feed is available).
  - Each `<img>` tag is dynamically updated by JavaScript to show the latest image for each camera.

3. **Debug Section**
  - Shows a live JSON dump of the device’s state as received from the backend API.
  - Useful for developers to see raw data and debug issues.

---
## Flask Server Log — What You’re Seeing

- The log shows the Flask development server starting up, running in debug mode, and listening on http://127.0.0.1:5000.
- Each line like `"GET /static/placeholder.jpg?... HTTP/1.1" 200 -` is a request from your browser to the server:
  - `GET /logout`, `GET /login`, `POST /login`, etc.: User navigation and authentication.
  - `GET /device/demo123`: Loading the device page.
  - `GET /static/styles.css`, `GET /static/device.js`: Loading static assets (CSS, JS).
  - `GET /api/device/demo123/state`: The frontend polling the backend for device state (for live updates).
  - `GET /static/placeholder.jpg?...`: The browser requesting the placeholder image for the camera feeds.
  - Status codes: `200` (OK), `302` (redirect), `304` (not modified, browser uses cached version).

- The server is working as expected: serving pages, static files, and API responses. The repeated requests for `/api/device/demo123/state` and `/static/placeholder.jpg` are due to the frontend polling for updates and refreshing camera images.

---
# Smart Post � User Persistence (users.json)

This branch builds on the existing landing page branch and adds **user permanence** to the existing login/signup flow by persisting users to a local JSON file.

> Scope note: This branch does **not** change the landing page UI. It only adds persistence for user accounts.


## What�s included

### User persistence (JSON file)
- Users are stored in `users.json` in the app root (same folder as `app.py`).
- Passwords are stored **hashed** (Werkzeug) � no plaintext passwords.
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


## Testing user persistence

1. Run the application:
2. Create a new user using `/signup`
3. Stop the server and restart it
4. Log in with the same user credentials
5. You will be redirected to the device page, confirming users are loaded from JSON