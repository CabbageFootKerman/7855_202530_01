# Sprint 2 Report

**Format:** Add the markdown (`docs/sprint2-report.md`) to your repo and submit the PDF to Learning Hub  
**Purpose:** This report is a **written companion** to your live demo. It summarizes **what you planned**, **what you delivered**, and **what you learned**.

---

## 1. Sprint Overview

- **Your Team Name:** [**Team Name Here**]  
- **Sprint 2 Dates:** [**Start → End**]  
- **Sprint Goal:** 
    *Example: Implement feature X with **Firestore persistence** and **basic validation**.*

---

## 2. Sprint Board

**Sprint Board Link:** [**Paste your Trello/GitHub Project link here**]  
**GitHub Repository Link:** [**Paste your repository link here**]

---

### 2.1 Sprint Board Screenshot (Filtered by Team Member)

**Please provide a screenshot of your Sprint 2 board** (e.g., Trello, GitHub Projects) **filtered by each team member**. This makes the review concrete and shows shared ownership.

- **[Member Name 1] Board Screenshot:**  
  `images/sprint2-board-filter-[member-name-1].png`

- **[Member Name 2] Board Screenshot:**  
  `images/sprint2-board-filter-[member-name-2].png`

(Repeat for each member.)

---

### 2.2 Completed vs. Not Completed (Feature-Focused)

Based on what you **plan** vs. what you **demoed**, summarize the state of your feature.

**Completed in Sprint 2 (Feature)**

- [ ] **Client** can trigger the feature and send input (e.g., POST `/feature`)
- [ ] **Server** exposes the endpoint with basic validation
- [ ] **Firestore** integration: data is written to the database
- [ ] **Server** can retrieve the stored data (GET from Firestore)
- [ ] **Basic Testing**: at least one test covering the happy path (or a validation test)
- [ ] **Security/Secrets**: credentials are not committed; `.gitignore` excludes sensitive files (e.g., `serviceAccountKey.json`, `.env`)

**Not Completed / Partially Completed**

- [ ] [**Feature/Task Name**]: [Brief reason: e.g., under‑estimated complexity, credential setup, blocked by Firestore rules, time constraint, ran out of Sprint]

---

## 3. Technical Summary: What Was Implemented

This is a **short technical summary** of the **end-to-end feature** you built.

- **Feature:** [**Feature Name**]  
- **Collection:** [**Firestore collection**] (e.g., `features`, `orders`, etc.)  
- **What it does:** [1–2 sentence description]

### Data Model (Firestore)

- **Document shape:**  
  Example JSON that represents **one document** in the collection (or the schema you structured):

  ```json
  {
    "id": "generated-id",
    "userId": "firebase-uid",
    "name": "Example Name",
    "status": "pending",
    "createdAt": "2026-01-01T12:00:00.000Z"
  }
  ```

  **Why this structure?** [Brief rationale: e.g., “We use `userId` to enforce per-user ownership, and `createdAt` for ordering.”]

- **Input (Client → Server):**  
  Example JSON the client sends:

  ```json
  {
    "name": "New Feature",
    "status": "pending"
  }
  ```

- **Output (Server → Client):**  
  Example response the client receives after a successful create or read:

  ```json
  {
    "id": "generated-id",
    "userId": "firebase-uid",
    "name": "New Feature",
    "status": "pending",
    "createdAt": "2026-01-01T12:00:00.000Z"
  }
  ```

---

## 4. End-to-End Flow (What Was Demoed)

Give a **high-level, end-to-end description** of the feature flow you demonstrated. This is the same flow you walked through in the demo, in written form.

1. **Client** sends a request to the server (e.g., POST `/feature`) with a valid **payload** (JSON).
2. **Server** validates the input and **requires authentication** (JWT verification via Firebase Admin).
3. **Server** creates or updates a document in **Firestore**, storing it under a collection (e.g., `/features`).
4. **Client** receives a response (e.g., 201 or 200) with the stored data.
5. **Client** requests the data (e.g., GET `/feature/:id`) and the server reads the document **specifically** from Firestore.
6. **Server** returns the data to the client.

**Bounded Read:** In Sprint 2, you were required to demonstrate a **bounded read** (e.g., `.limit()`, `.where()`, or pagination). Describe what you implemented:

- **What you did:** [e.g., “We used Firestore `.limit(10)` to fetch a maximum of 10 items per request.”]
- **Why this matters:** [e.g., “This prevents unbounded scans, protects cost, and improves performance as data grows.”]

---

## 5. Sprint Retrospective: What We Learned

### 5.1 What Went Well

- [Item 1: e.g., “We got end-to-end persistence working faster than expected.”]
- [Item 2: e.g., “We agreed on a consistent validation strategy for the request.”]
- [Item 3: e.g., “Our team communication and coordination improved this sprint.”]

### 5.2 What Didn’t Go Well

- [Item 1: e.g., “We underestimated the time needed to set up Firebase credentials and permissions.”]
- [Item 2: e.g., “Our tests were delayed and didn’t cover all edge cases by demo time.”]
- [Item 3: e.g., “We had integration friction between the client and server around payload format.”]

### 5.3 Key Takeaways & Sprint 3 Actions

| Issue / Challenge | What We Learned | Action for Sprint 3 |
|---|---|---|
| [Issue 1] | [Learning] | [Action] |
| [Issue 2] | [Learning] | [Action] |
| [Issue 3] | [Learning] | [Action] |

---

## 6. Sprint 3 Preview

Based on what we accomplished (and what we didn’t), here are the **next Sprint 3 priorities**:

- [**Priority 1**: e.g., “Add user authentication and authorization so users can only access/modify their own feature data.”]
- [**Priority 2**: e.g., “Expand testing coverage (unit + integration) and implement clearer error handling.”]
- [**Priority 3**: e.g., “Improve read performance with pagination and/or where clauses.”]
