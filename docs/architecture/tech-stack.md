## Tech Stack

| Category | Technology | Version | Purpose | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Language** | Python | 3.11 | Primary language for all backend logic. | Modern, robust, and has an extensive ecosystem for AI and web services. |
| **Backend Framework**| FastAPI | 0.111.0 | Provides the structure for our backend service. | High performance, excellent for building APIs, and has automatic documentation. |
| **AI Framework** | LangGraph | Latest | Manages the stateful, cyclical AI logic. | Provides explicit, stateful control over complex processes, a perfect fit for a rule-heavy game loop. |
| **Bot Interface** | discord.py | 2.3.2 | Connects our application to the Discord API. | The leading and most robust library for creating Discord bots in Python. |
| **Data Persistence** | Polyglot | N/A | Flexible data storage. | Uses the best tool for each job: SQLite for rules, and YAML/JSON for campaign files. |
| **Containerization** | Docker / Docker Compose | Latest | Packages the application for portability. | Simplifies local self-hosting and ensures consistent deployment environments. |
| **Testing Framework**| Pytest | 8.2.2 | For all unit and integration tests. | The standard for Python testing; powerful, flexible, and has a rich plugin ecosystem. |