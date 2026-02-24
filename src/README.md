# SmartPost Notification System Scaffold (Web Demo + Future Mobile-Oriented)

## Overview

This change adds a **notification system scaffold** to the SmartPost Flask app.

The goal of this work is to provide a **clean, extensible notification structure** that:
- works immediately in the current web app,
- demonstrates integration with the existing device workflow,
- stores notifications persistently in Firestore,
- leaves clear extension points for teammates to implement:
  - web push notifications,
  - mobile push notifications,
  - recipient routing (device owners/shared users),
  - preferences, retries, and background delivery.

This is **not** a production-complete notification platform yet. It is a working scaffold with a live demo UI and testable API flow.

---

## Scope of This Change

### Backend (`app.py`)
Added:
- Notification orchestration service (`NotificationService`)
- Channel interface (`NotificationChannel`)
- Firestore-backed channels:
  - global event log channel
  - per-user inbox channel
- Stub channels for future delivery:
  - web push stub
  - mobile push stub
- Notification publishing helper for device events
- Demo recipient resolver (current user only)
- Notification API routes:
  - list notifications
  - unread count
  - mark one as read
  - mark all as read
- Demo notification endpoint (`/api/device/<device_id>/demo-notify`)
- Integration into existing device command route (`/api/device/<device_id>/command`) so command actions generate notifications

### Frontend (`templates/device.html`)
Added:
- Notification bell UI with unread badge
- Notification panel/dropdown
- “Check Notifications” button
- Demo notification buttons
- Polling (10s) for unread count and list refresh
- Mark-read + mark-all-read actions
- Status messaging in the notification panel

---

## Architecture Summary

The notification system is intentionally split into layers:

1. **Event generation**  
   A route or subsystem emits a notification event (example: device command sent, package detected).

2. **Notification orchestration**  
   `NotificationService.publish(...)` creates a standard payload and fans out to registered channels.

3. **Channel delivery**  
   Current channels:
   - Firestore global event log (debug/audit/demo)
   - Firestore per-user inbox (in-app notifications)

   Placeholder channels:
   - Web push (stub)
   - Mobile push (stub)

This design allows teammates to add new delivery methods later without changing route logic.

---

## Firestore Data Structure (Current Scaffold)

### Global notification event log
Collection:
- `notification_events/{event_id}`

Purpose:
- records all generated events for debugging/demo/auditing

### Per-user notification inbox
Collection:
- `users/{username}/notifications/{event_id}`

Purpose:
- stores in-app notifications shown in the notification panel
- supports read/unread state

---

## Notification Payload Shape (Current Scaffold)

Typical fields written into user notification docs include:

- `schema_version`
- `event_id`
- `type`
- `title`
- `body`
- `severity` (`info`, `success`, `warning`, `error`)
- `actor_username`
- `device_id`
- `data` (extensible metadata)
- `created_at_client_iso`
- `created_at` (Firestore server timestamp)
- `updated_at` (Firestore server timestamp)
- `read` / `read_at`
- `delivery` (status placeholders for in-app / web_push / mobile_push)

---

## Current Behavior (Important)

### Recipient resolution (temporary/demo behavior)
Notifications are currently sent to the **logged-in user only**.

This is intentional and isolated in:
- `resolve_notification_recipients_for_device(...)`

Teammates can later replace this with:
- device ownership lookup
- shared users
- role-based routing
- notification preferences / mute rules

---

## API Endpoints Added / Updated

## Existing route now integrated with notifications
### `POST /api/device/<device_id>/command`
- Existing command route (`open` / `close`)
- Now also generates a notification (`device_command`) on success

---

## New notification APIs

### `GET /api/notifications`
Returns recent notifications for the logged-in user.

Query params:
- `limit` (default `20`, clamped to `1..100`)
- `unread_only` (`true/false`)

---

### `GET /api/notifications/unread-count`
Returns unread notification count for the logged-in user.

---

### `POST /api/notifications/<notification_id>/read`
Marks a single notification as read.

---

### `POST /api/notifications/read-all`
Marks all unread notifications as read for the logged-in user.

---

### `POST /api/device/<device_id>/demo-notify`
Creates demo notifications without real hardware events.

Supported presets:
- `package_detected`
- `door_left_open`
- `device_offline`

Request JSON example:
```json

{"preset": "package_detected"}

```
---

## Image Upload & Retrieval (Firestore-Tracked, Local Storage)

### Overview
This change adds **image upload and retrieval support** to the SmartPost Flask application.

The goal is to demonstrate:
- transferring image data from a device-facing client to the server,
- persisting **meaningful metadata in Firestore**,
- listing available images per device,
- and allowing authenticated users to download images.

Images are stored **locally on the Flask server**, while Firestore is used as the authoritative index and metadata store.

This design avoids committing binary media to the repository while still demonstrating persistent backend tracking.

---

### Backend Behavior
When an image is uploaded:

1. The file is saved locally under: src/uploads/device_<device_id>/<uuid>.<ext>
2. A Firestore document is created in: media_uploads/{upload_id}

Each document records metadata including:
- `device_id`
- original filename
- stored filename
- relative file path
- MIME type
- file size
- upload timestamp
- expiration timestamp (TTL)

3. A notification event is generated confirming the upload.

Image metadata is later queried to:
- list available images for a given device,
- validate expiration,
- and locate the file for download.

---

### API Endpoints Added

#### Upload image (device → server)

POST /api/device/<device_id>/upload-image
- Accepts multipart form data with field name `image`
- Stores the image locally
- Writes metadata to Firestore
- Returns an upload ID on success

---

#### List available images (user → server)
GET /api/media?device_id=<device_id>

- Queries Firestore for images associated with the device
- Filters out expired entries
- Returns metadata for available downloads

---

#### Download image
GET /api/media/<upload_id>/download

- Validates metadata and expiration
- Serves the file from local storage
- Forces download with the original filename

---

### Firestore Index Requirement (Important)
The image listing query filters by `device_id` and orders by creation time.  
Firestore requires a **composite index** for this query shape.

On first run, Firestore may return: The query requires an index

When this occurs:
- Follow the link provided in the error message
- Create the suggested index (one-time, per Firebase project)

Once created, no further action is required for that project.

---

### Local Setup Notes (Firestore Credentials)
This project does **not** commit Firebase credentials.

To run locally:
- Place `serviceAccountKey.json` at the repository root  
  **or**
- Set the environment variable: FIREBASE_KEY_PATH=<path to serviceAccountKey.json>

Each developer may use their own Firebase project during local development.  
Firestore indexes are created **once per project**, not per user or per run.

---

### Scope Notes
- Images are stored locally for demo purposes.
- Firestore acts as the persistent metadata/index layer.
- This is sufficient to demonstrate file transfer, persistence, and retrieval for the sprint.
- Video support can be added later using the same pattern.