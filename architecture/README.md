# SmartPost WAN Robot Control

## Architectural Pattern Justification

We have adopted the **Client-Server pattern** for the SmartPost system. This divides the architecture into clients (web/mobile apps, SmartPost device) and a central cloud server handling authentication, commands, media storage, and notifications.

### Why Client-Server?

- **Separation of concerns:** Clients handle UI; server manages data and logic.
- **Centralized control:** Single source of truth for state and security.
- **Scalability:** Backend scales independently of clients.
- **Extensibility:** New features or clients integrate easily.

This proven model fits our core requirements: remote access, user management, and media streaming from anywhere.

---

## System Diagrams

![Cloud Architecture](images/SmartPost_Cloud_db_architecture.png)
*Cloud-side components: server, databases, and storage.*

This architecture supports our MVP epics: enabling users to open/close the SmartPost remotely, stream video or photos, receive package notifications, and review footage from the last 24 hours.

![Context Diagram](images/ContextDgrmFlowChart.png)
*System boundaries, actors, and data flows.*

The context diagram shows how users and external services interact with the SmartPost system, reinforcing our goal of secure remote access from anywhere.

![MVP Sequence](images/MVP_sequence_diagram.png)
*Core flow: user remotely opens the SmartPost box.*

This sequence reflects the primary user story: "As a user, I should be able to open/close the SmartPost with internet access from anywhere in order to feel secure and in control."

![Software Components](images/SmartPost_SoftwareComponentChart.webp)
*Main modules and their interactions.*

The component diagram details how the client layer, service layer, and data layer communicate. We plan to use **tunnelmole.com** to connect the Raspberry Pi clients and control clients, enabling reliable WAN connectivity without complex network configuration.

---

## Trade-Offs

- **Single point of failure:** Mitigated by cloud redundancy and failover.
- **Potential bottleneck:** Addressed with scalable infrastructure.

The benefits—centralized security, maintainability, and extensibility—outweigh these risks for our use case.
