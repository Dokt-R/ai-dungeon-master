# Key Strategies

* **Error Handling:** A centralized handler, custom exceptions, and traceable logging will be used.
* **Coding Standards:** **Black** for formatting and **Ruff** for linting will be enforced. All code must adhere to the PEP 8 style guide.
* **Test Strategy:** **Pytest** will be used for both unit and integration tests.
* **Security:** Secrets will be managed via environment variables, and all inputs will be validated by Pydantic models.
* **Type Hints:** All function signatures and variable declarations must include full, correct type hints. This is critical for both code clarity and for the AI agents' understanding.
* **Naming Conventions:** snake_case for variables, functions, and modules. PascalCase for classes. Constants should be in ALL_CAPS.
* **Use the Abstraction Layers:** All data access must go through the MemoryService. Direct database calls from other components are forbidden.