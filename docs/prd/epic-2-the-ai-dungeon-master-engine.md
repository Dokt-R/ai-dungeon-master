# Epic 2: The AI Dungeon Master Engine

**Expanded Goal:** This epic breathes life into the core platform, integrating the AI language models to transform the bot from a simple command-handler into a living Dungeon Master. By the end of this epic, the bot will be able to run a basic D&D 5.1 SRD-compliant game, remember key events, and interact with players through both text and voice, delivering the core product promise.

---
### Story 2.1: Basic AI Narrative Generation
**As a** player, **I want** to send a prompt to the bot and receive a narrative response from the AI, **so that** I can begin to interact with the game world.
#### Tasks / Subtasks
- [ ] **Task 1 (Enabler):** Integrate the LLM Observability library (e.g., LangSmith) into the backend service to enable tracing for all future AI calls.
- [ ] **Task 2 (AC: #1):** Create a function that retrieves the server's API key from the `ServerConfig` database table.
- [ ] **Task 3 (AC: #1, #2, #3):** Implement the API endpoint (`/action`) that receives the player's prompt, calls the AI provider with the correct context and key, and returns the narrative response.
- [ ] **Task 4 (AC: #4):** Implement error handling for the AI API call.
#### Acceptance Criteria
1.  **The bot retrieves the server's encrypted API key from the `ServerConfig` database table** and uses it to send a user's text prompt to the specified AI service.
2.  The AI's text-based narrative response is successfully received from the service.
3.  The narrative response is displayed clearly in the Discord channel.
4.  The system gracefully handles and reports any errors during the AI API call.


---
### Story 2.2: D&D 5.1 SRD Ruleset Integration
**As a** player, **I want** the AI DM to be aware of the D&D 5.1 SRD rules, **so that** its rulings and descriptions are accurate and fair.
#### Acceptance Criteria
1. The AI's system prompt or context is primed with the D&D 5.1 SRD ruleset (e.g., via RAG or context priming).
2. The AI can correctly answer a direct question about a specific SRD rule (e.g., "How much damage does a longsword do?").
3. The AI's narrative descriptions correctly reference SRD mechanics (e.g., correctly describing a spell's effect or a monster's abilities).

> **Note for the Architect:** The user has suggested that instead of relying purely on text-based context priming, we should explore implementing specific, deterministic rules as callable **agent tools or server-side functions**. This hybrid approach could greatly improve accuracy and reduce long-term API costs. Please evaluate this during the architecture design phase.

---
### Story 2.3: Core Memory System Implementation
**As a** player, **I want** the AI DM to remember what has happened in our campaign, **so that** the story is coherent and my actions have lasting impact.
#### Acceptance Criteria
1. The system can create, read, update, and delete key events or facts for an active campaign (e.g., "Player met NPC Gundren," "The party cleared the goblin cave").
2. The AI's context for generating a new response includes relevant memories from the current campaign.
3. The AI can demonstrate recall by referencing a past event in its narrative when prompted or appropriate.
4. The campaign memory persists between bot restarts.

---
### Story 2.4: Voice Interaction Integration
**As a** player, **I want** to be able to speak to the AI DM and hear it speak back, **so that** I can have an immersive, hands-free gameplay experience.
#### Acceptance Criteria
1. The bot can join a Discord voice channel.
2. The bot can listen to and accurately transcribe a player's spoken words into a text prompt.
3. The AI's text response is successfully converted to speech audio.
4. The generated audio is played back to the user in the voice channel.
5. The average roundtrip latency (from end of user speech to beginning of bot speech) for a standard interaction meets the `NFR1` target of under 4 seconds.

