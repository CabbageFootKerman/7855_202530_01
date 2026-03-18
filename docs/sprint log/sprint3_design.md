# Sprint 3 Report

- **Team Name:** SmartPost WAN Robot Control  
- **Sprint Dates:** [Start ? End]  
- **Sprint Board Link:** [Link]  
- **GitHub Repository Link:** [Link]


## 1. Sprint Board Screenshots
*Provide screenshots of your Sprint 3 board filtered by each team member.*
**Team Members:**
1. Pawel Banasik
2. Mikhail Rego
3. Glen Healy
4. Ryan McKay

- **Pawel Banasik:** `images/sprint3-board-pawel.png`
- **Mikhail Rego:** `images/sprint3-board-mikhail.png`
- **Glen Healy:** `images/sprint3-board-glen.png`
- **Ryan McKay:** `images/sprint3-board-ryan.png`

## 2. Sprint Review (Planned vs. Delivered)
*Review what you planned to accomplish this sprint versus what was actually completed. Focus on your architecture, testing, and UI goals.*


**Successfully Delivered:**
- Modularized the Flask app using blueprints for each feature (auth, dashboard, device, media, profile, notifications).
- Set up Firestore integration and device provisioning scripts (seed_device.py, firebase.py).
- Implemented device state and command APIs, including dummy device simulation (dummy_box.py).
- Created notification system scaffold with persistent storage and demo endpoints.
- Added Jinja2 templates for device, login, signup, and dashboard views.

**Not Completed / Partially Completed:**
- Full test coverage for all endpoints (pytest setup is present, but some endpoints lack tests).
	- Underestimated the time required for mocking Firestore and writing parametrized tests.
- Real device integration (dummy_box.py is a placeholder, needs further testing and modification).
	- Still in development; dummy simulation needs to be connected to the API and validated.
- Mobile push notification delivery (scaffold present, but not fully implemented).
	- Awaiting team member availability and further research on delivery channels.

## 3. Architecture & UI Strategy

**Code Modularization:**  
The src folder uses a blueprint-based modular architecture. Each feature (auth, dashboard, device, media, profile, notifications) is separated into its own subfolder under blueprints/.
app.py acts as the central entry point, handling initialization, config, and blueprint registration.
Utility functions are organized in utils/, and route guards in decorators/.
Templates and static assets are separated for clarity and maintainability.

**How app.py was broken apart:**  
Instead of putting all routes and logic in app.py, each feature area (e.g., device, media, notifications) has its own blueprint and routes file.
app.py only handles setup and registration, making the codebase easier to extend and test.

**SSR + CSR Breakdown:**  
- **Server-Side (Flask):** Renders base templates, handles authentication, device pages, and notification inbox. Provides initial layout and data for each page.
- **Client-Side (JS):** Handles dynamic updates, such as fetching device state, updating UI elements, and managing live interactions (e.g., opening/closing the SmartPost box, updating notifications).

## 3a. Architecture & UI Specification Document

The architecture and UI specification document is stored in docs/sprint3_design.md and has been submitted as a PDF as required.

## 3b. Security Measures

**Input Validation & Query Limits:**
- Input validation is implemented using Flask request validation and custom decorators.
- Query limits are enforced via Flask-Limiter to prevent abuse and ensure fair usage.
- All API endpoints check for required fields and types, and user permissions are validated before processing requests.
- Uploaded files are checked for allowed extensions and securely stored.

## 4. Automated Testing & Coverage
- **Testing Framework:** `pytest`
- **Current Code Coverage:** Automated testing and coverage will be completed in the next week of this sprint.
- **Mocked Components:** Firestore, device state, authentication/session helpers (planned).

**Test Highlight:**
*Test highlight will be added after coverage is implemented.*
