# Implementation Plan: SQLModel-Based Persistent Game State

## 1. Overview

This document provides a detailed, step-by-step implementation plan for standardizing all game state entities (state models, characters, NPCs, items) as SQLModel-based persistent objects. This plan is based on the comprehensive analysis of the strategic implications, advantages, and disadvantages of this architectural shift.

The goal is to transition from a hybrid in-memory/JSON blob persistence model to a fully relational, database-backed state management system. This will enhance data integrity, scalability, and observability. The plan is divided into three main phases to mitigate risk and allow for iterative development and testing.

## 2. Phase 1: Foundational Work - Unifying Models and a Data Access Layer (DAL)

**Goal:** Establish a single source of truth for data models and abstract database interactions. The game will still operate on an in-memory state, but the loading and saving will be based on a rich, relational structure.

**Estimated Timeframe:** 2-3 sprints

### 2.1. Design & Planning (Sprint 1)

-   **Task 2.1.1: Finalize Unified SQLModel Schema**
    -   Merge the fields from `packages/backend/ai/state/base_state.py` (Pydantic models) into the SQLModel definitions in `packages/shared/models/core_db_models.py`.
    -   Define relationships for:
        -   `Character` to `Item` (Inventory, Equipped Items)
        -   `Campaign` to `Character` (NPCs and PCs in the campaign)
        -   `Room` to `Character` and `Item`
    -   Create new SQLModel tables for `Item`, `Room`, `NPC`, etc.
    -   **Output:** A finalized `core_db_models.py` with the complete relational schema.

-   **Task 2.1.2: Design the Data Access Layer (DAL)**
    -   Define the interface for the DAL. It should provide CRUD operations for all game entities (e.g., `get_character`, `update_character`, `add_item_to_inventory`).
    -   The DAL will be responsible for managing database sessions.
    -   **Output:** An interface definition for the DAL.

### 2.2. Implementation (Sprint 2)

-   **Task 2.2.1: Implement the Unified SQLModels**
    -   Implement the new schema in `core_db_models.py`.
    -   Set up Alembic for database schema migrations.
    -   **Output:** A new version of `core_db_models.py` and initial Alembic migration scripts.

-   **Task 2.2.2: Implement the DAL**
    -   Create a new `packages/backend/dal` module.
    -   Implement the DAL class with methods for all the defined CRUD operations.
    -   **Output:** A functional DAL.

### 2.3. Integration & Migration (Sprint 3)

-   **Task 2.3.1: Adapt Game State Manager**
    -   Modify the `GameStateManager` to use the DAL to load the full game state from the database into the in-memory Pydantic objects at the start of a session.
    -   Modify the `GameStateManager` to use the DAL to persist the state back to the database at save points.
    -   **Output:** An updated `GameStateManager`.

-   **Task 2.3.2: Data Migration Strategy**
    -   Develop scripts to migrate existing campaign data from the `MemoryStateModel` JSON blob to the new relational schema.
    -   The script should be idempotent and testable.
    -   **Output:** A data migration script.

### 2.4. Testing

-   Unit tests for all DAL methods.
-   Integration tests for the `GameStateManager` to ensure that loading and saving work correctly.
-   Tests for the data migration script.

## 3. Phase 2: Hybrid Model - Direct DB Operations for Low-Frequency Actions

**Goal:** Start leveraging the database for live game operations in a controlled manner to evaluate performance and identify challenges.

**Estimated Timeframe:** 2 sprints

### 3.1. Implementation (Sprint 4)

-   **Task 3.1.1: Identify and Refactor Low-Frequency Nodes**
    -   Identify AI nodes that handle non-performance-critical actions (e.g., inventory management, character sheet updates, looting).
    -   Refactor these nodes to use the DAL directly to modify the database.
    -   This will require passing a DAL instance or a database session to the nodes.
    -   **Output:** Refactored AI nodes.

-   **Task 3.1.2: Implement Caching**
    -   Introduce a caching layer (e.g., Redis) for frequently accessed, rarely changed data (e.g., SRD item definitions).
    -   Integrate the cache with the DAL.
    -   **Output:** A caching layer integrated with the DAL.

### 3.2. Testing & Performance Analysis (Sprint 5)

-   **Task 3.2.1: Integration Testing**
    -   Write integration tests for the refactored AI nodes to ensure they correctly modify the database.
    -   **Output:** New integration tests.

-   **Task 3.2.2: Performance Testing**
    -   Benchmark the performance of the refactored nodes.
    -   Compare the performance with the old in-memory operations.
    -   **Output:** A performance analysis report.

## 4. Phase 3: Full Transition - Database as the Single Source of Truth

**Goal:** Complete the transition to a fully database-backed state management system.

**Estimated Timeframe:** 3-4 sprints

### 4.1. Implementation (Sprints 6-7)

-   **Task 4.1.1: Refactor High-Frequency Nodes**
    -   Rewrite the combat, exploration, and other performance-critical nodes to work directly with the database via the DAL.
    -   This will require careful query optimization and extensive use of the caching layer.
    -   **Output:** Refactored high-frequency AI nodes.

-   **Task 4.1.2: Implement Transaction Management**
    -   Implement transaction management within the AI graph to ensure that complex actions (e.g., an attack) are atomic.
    -   This could be implemented as a decorator or middleware for the AI nodes.
    -   **Output:** A transaction management system for the AI graph.

### 4.2. Finalization (Sprint 8)

-   **Task 4.2.1: Deprecate In-Memory State Blob**
    -   Remove the concept of loading the entire game state into memory at the start of a session.
    -   The `GameStateManager` will become a thin wrapper around the DAL, loading data on demand.
    -   **Output:** A simplified `GameStateManager`.

-   **Task 4.2.2: Final Data Migration**
    -   Run the final data migration scripts in a staging environment.
    -   Perform a full data validation.
    -   **Output:** A validated, migrated database.

### 4.3. Deployment (Sprint 9)

-   **Task 4.3.1: Staging Deployment and Testing**
    -   Deploy the new system to a staging environment.
    -   Conduct extensive end-to-end testing, including performance and stress testing.
    -   **Output:** A successful staging deployment.

-   **Task 4.3.2: Production Deployment**
    -   Schedule a maintenance window for the production deployment.
    -   Run the data migration scripts.
    -   Deploy the new application.
    -   Monitor the system closely.
    -   **Output:** A successful production deployment.

## 5. General Considerations

-   **Observability:** Throughout all phases, enhance logging and tracing to monitor database performance and identify bottlenecks.
-   **Documentation:** Keep the architectural and data model documentation up to date.
-   **Team Training:** Ensure the development team is comfortable with the new data access patterns and technologies.