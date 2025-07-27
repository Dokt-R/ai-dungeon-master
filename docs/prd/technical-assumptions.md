# Technical Assumptions

### Repository Structure: Monorepo
The project will be housed in a single monorepo.
* **Rationale**: For a solo developer, a monorepo simplifies dependency management, streamlines the build process, and makes it easier to share code and types between the AI backend and any future front-end applications (like the PC App).

### Service Architecture
The architecture will be **service-oriented**, as specified in the brief. For the MVP, this will likely be implemented as a **Modular Monolith**.
* **Rationale**: This approach allows for clear separation of concerns and logical service boundaries from day one, while avoiding the operational complexity of deploying multiple microservices for the MVP. It provides a clear path to scale out to true microservices post-MVP if needed.

### Testing Requirements
The project will require, at a minimum, **Unit and Integration tests**.
* **Rationale**: This ensures that individual components work as expected (Unit tests) and that they connect and interact correctly (Integration tests), providing a solid foundation of quality for the MVP.

### Additional Technical Assumptions and Requests
* **Primary Backend Language**: The backend will be developed in **Python**.
* **AI Framework**: We will explore agentic frameworks like **CrewAI** to manage the AI DM's logic.
* **Data Persistence**: The project will adopt a **flexible persistence strategy**, using the most appropriate storage solution for each type of data. The Architect will determine the best tool for each use case, which may include options like pre-built memory systems within AI frameworks, file-based storage (YAML, JSON), or a traditional database (SQL or NoSQL).
* **Security**: The system must be designed for the secure handling of user-provided API keys.
