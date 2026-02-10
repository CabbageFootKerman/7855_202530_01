# SmartPost WAN Robot Control

**Course:** Software Systems  
**Status:** In Development

**Team Members:**
1. Pawel Banasik: I don't like defining myself, don't make me do it. I like puzzles and coding, and coming up with innovative solutions to problems, that's about all that I will say.
2. Mikhail Rego: I am a curious, apprentice engineer who has a natural talent for organizing things and telling people "they're not doing doing what they're supposed to :yum:." Fun fact: I am crazy into both hard-core rock and hard-core country.
3. Glen Healy: I'm interested in building some cool electrical and software projects this semester. this is a second test.
4. Ryan McKay: My favourite animal is the humble box jellyfish

## Project Overview

SmartPost is a smart package delivery box system that allows users to securely receive packages and control their SmartPost unit remotely from anywhere via web or mobile app. The system uses a Raspberry Pi as a central server, exposed to the internet via Tunnelmole, enabling features such as:

- Remote open/close control of the SmartPost box
- Live video streaming and photo capture
- Package arrival notifications
- Review of footage from the last 24 hours
## Folder Structure

```
code/
├── src/    # Source code for core modules and services
├── docs/   # Documentation, design notes, and diagrams
├── tests/  # Automated and manual test cases
├── README.md
└── ...
```

## 🚀 Start Here: App Location

👉 **[Go to the app source folder (src/)](src/)** — The main application entry point is in [src/app.py](src/app.py).

## Architectural Choices

We use a **Client-Server architecture** with a **Layered (N-Tier) organization**. The Raspberry Pi server acts as the central hub, maintaining the source of truth for permissions and device state, while clients (web, mobile, connected unit) interact via Tunnelmole for secure remote access.

For detailed architectural pattern justification, system diagrams, and trade-offs, see:  
👉 [Architecture Documentation](docs/architecture/README.md)

---
This repository is initialized and ready for collaborative development. Please see the `docs/` folder for further details and design documents.
