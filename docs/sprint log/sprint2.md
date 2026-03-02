# Sprint 2 Report

**Format:** Add the markdown (`docs/sprint2-report.md`) to your repo and submit the PDF to Learning Hub  
**Purpose:** This report is a **written companion** to your live demo. It summarizes **what you planned**, **what you delivered**, and **what you learned**.

---

## 1. Sprint Overview

- **Your Team Name:** SmartPost Team  
- **Sprint 2 Dates:** Tuesday 3 weeks ago until today  
- **Sprint Goal:** Store user data on cloud with Firestore. And try to connect to a version of our server app on a raspberry pi remotely.

---

## 2. Sprint Board

**Sprint Board Link:** https://trello.com/b/yflbxHFP/comp7855202610-team1  
**GitHub Repository Link:** https://github.com/CabbageFootKerman/7855_202530_01

---

### 2.1 Sprint Board Screenshot (Filtered by Team Member)

**Please provide a screenshot of your Sprint 2 board** (e.g., Trello, GitHub Projects) **filtered by each team member**. This makes the review concrete and shows shared ownership.

- CodeNube737 (Mikhail R)
- CabbageFootKerman (Pawel B)
- Raevz (Ryan M)
- HealyElectrical (Glen Healy) 
- **Members Board Screenshot:**  
  `images/sprint2.jpeg`

---

### 2.2 Completed vs. Not Completed (Feature-Focused)

Based on what you **plan** vs. what you **demoed**, summarize the state of your feature.

**Completed in Sprint 2 (Feature)**

- [x] **Client** can trigger the feature and send input (e.g., POST `/feature`)
- [x] **Server** exposes the endpoint with basic validation
- [x] **Firestore** integration: data is written to the database
- [x] **Server** can retrieve the stored data (GET from Firestore)
- [x] **Basic Testing**: at least one test covering the happy path (or a validation test)
- [x] **Security/Secrets**: credentials are not committed; `.gitignore` excludes sensitive files (e.g., `serviceAccountKey.json`, `.env`)

**Not Completed / Partially Completed**

- None. All planned features were completed.

---

## 3. Technical Summary: What Was Implemented

This is a **short technical summary** of the **end-to-end feature** you built.

- **Feature:** Firestore cloud storage & Notification System Scaffold (SmartPost)
- **Collection:** `notification_events` (global event log), `users/{username}/notifications` (per-user inbox)
- **What it does:** Adds a notification system to the SmartPost app, allowing device events and commands to generate notifications that are stored in Firestore and displayed in the web UI. The system supports per-user inboxes, read/unread state, and is designed for future extension to web/mobile push delivery. The main updates in Sprint 2 were to Firestore storage and the REST API protocol, enabling persistent notification data and standardized client-server communication.

### Data Model (Firestore)

- **Document shape:**  
  Example JSON that represents **one document** in the collection:

  ```json
  {
    "event_id": "auto-generated-id",
    "userId": "firebase-uid",
    "type": "device_event",
    "title": "Device Command Executed",
    "body": "Command sent to device successfully.",
    "status": "unread",
    "createdAt": "2026-03-02T12:00:00.000Z",
    "device_id": "device-123",
    "actor_username": "user@example.com"
  }
  ```

  ![Firestore Document Example](images/firestore_sprint2.jpeg)

  **Why this structure?** We use `userId` to enforce per-user ownership, `id` for unique identification, and `createdAt` for reliable ordering and audit history. The `status` and `name` fields allow flexible notification content and tracking. This schema supports scalable, secure, and user-specific notification delivery.

- **Input (Client → Server):**  
  Example JSON the client sends (e.g., POST to `/api/device/demo123/command`):

  ```json
  {
    "command": "open"
  }
  ```

- **Output (Server → Client):**  
  Example response the client receives after a successful command:

  ```json
  {
    "message": "Command 'open' received for demo123.",
    "notification": {
      "status": "ok",
      "event_id": "auto-generated-id",
      "recipient_count": 1,
      "deliveries": [
        {"channel": "firestore_event_log", "status": "ok", "logged_event_id": "auto-generated-id"},
        {"channel": "firestore_user_inbox", "status": "ok", "writes": 1},
        {"channel": "web_push_stub", "status": "skipped", "reason": "stub_not_implemented", "recipient_count": 1},
        {"channel": "mobile_push_stub", "status": "skipped", "reason": "stub_not_implemented", "recipient_count": 1}
      ]
    }
  }
  ```

---

## 4. End-to-End Flow (What Was Demoed)

The demo showcased the full notification and device command flow:

1. **Client** sends a POST request to the server (e.g., `/api/device/demo123/command`) with a valid JSON payload (such as `{ "command": "open" }`).
2. **Server** validates the input and requires authentication (user must be logged in; session-based in Flask).
3. **Server** processes the command and publishes a notification using the NotificationService, which writes to Firestore collections (`notification_events` and `users/{username}/notifications`).
4. **Server** responds to the client with a success message and notification delivery details.
5. **Client** can request notifications (e.g., GET `/api/notifications`) and the server reads the user's notification documents from Firestore.
6. **Server** returns the notification data to the client, supporting unread filtering and pagination.

**Bounded Read:**

- **What you did:** Used Firestore `.limit()` and `.order_by()` in notification and media queries to fetch a maximum number of items per request (e.g., limit 20 or 50, newest first).
- **Why this matters:** This prevents unbounded scans, controls cost, and ensures fast performance as data grows, while supporting efficient pagination and filtering for the client UI.

---

## 5. Sprint Retrospective: What We Learned

### 5.1 What Went Well

- We achieved reliable end-to-end persistence and notification delivery using Firestore.
- Our REST API endpoints worked smoothly and were easy to test and demo.
- Team members collaborated well, sharing code reviews and troubleshooting together.

### 5.2 What Didn’t Go Well

- Initial setup of Firebase credentials and permissions took longer than expected.
- Some edge cases in notification delivery and error handling were only discovered late in the sprint.
- We could have made better use of user stories and epics to guide our task selection and prioritization.

### 5.3 Key Takeaways & Sprint 3 Actions

| Issue / Challenge | What We Learned | Action for Sprint 3 |
|---|---|---|
| Firebase setup delays | Credential management is critical and should be planned early | Document setup steps and automate environment checks |
| Late edge case discovery | Early testing helps catch issues sooner | Expand test coverage and add integration tests |
| Task planning | User stories and epics help clarify priorities | Use stories/epics to drive sprint planning and reviews |

---

## 6. Sprint 3 Preview

Based on what we accomplished (and what we didn’t), here are the **next Sprint 3 priorities**:

- **Set up Raspi Tunnelmole:** Build hardware and establish a secure tunnel to connect our Raspberry Pi to the internet.
- **Deploy server online:** Get our SmartPost server running and accessible from the web.
- **Build & test SmartPost API:** Develop and test a robust API for SmartPost clients to interact with the server.
- **Connect Glen's box:** Integrate Glen's home device with the server for real-world testing and feedback.
- **Sprint planning:** Meet as a team to finalize user stories, epics, and priorities for Sprint 3.
