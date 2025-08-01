# **Coding Standards**

These standards are mandatory for all code, whether written by AI or human developers, to ensure consistency, readability, and quality.This section is designed to be minimal, focusing on project-specific conventions and rules that AI agents might otherwise violate.

---
## **Core Standards**
* **Languages & Runtimes:** All specified language and runtime versions in the Tech Stack must be adhered to.
* **Style & Linting:** All code must be auto-formatted with the selected linter and formatter (e.g., Black for Python).
* **Test Organization:** Test files must follow the defined convention (e.g., located in a `tests/` directory and mirroring the application structure).

---
## **Naming Conventions**

This table defines the required naming conventions for different code elements.

| Element | Frontend | Backend | Example |
| :--- | :--- | :--- | :--- |
| Components | PascalCase | - | `UserProfile.tsx` |
| Hooks | camelCase with 'use' | - | `useAuth.ts` |
| API Routes | - | kebab-case | `/api/user-profile` |
| Database Tables | - | snake_case | `user_profiles` |


---
## **Critical Rules**

This is a non-exhaustive list of critical rules that must be followed to prevent common errors.
* **Use the Logger:** Never use `print()` or `console.log()` statements in production-level code; use the configured logging service.
* **Use the Abstraction Layer:** All database queries must go through the defined repository or data service layer. Direct ORM or database calls from business logic are forbidden.
* **Standard API Responses:** All API responses must use the standardized wrapper type defined in the architecture.
* **No Hardcoded Secrets:** Never hardcode secrets (API keys, passwords) in the source code. They must be loaded from the configuration service or environment variables.