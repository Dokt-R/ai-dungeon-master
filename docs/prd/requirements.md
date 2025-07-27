# Requirements

### Functional Requirements
1.  **FR1**: The system shall support both text-based and voice-based interaction for all core gameplay loops.
2.  **FR2**: The AI DM engine must adjudicate gameplay using the Dungeons & Dragons 5.1 SRD ruleset.
3.  **FR3**: The system must have a core memory system capable of recalling key NPCs, locations, and plot events within a single campaign.
4.  **FR4**: The platform must provide a user interface for server owners to securely input and manage a server-wide API key for the BYOK model.
5.  **FR5**: The MVP of the platform must be delivered as an installable Discord bot.
6.  **FR7**: The AI DM must support a foundational system for narrative control, allowing for different DMing styles (e.g., a "Dynamic World" that creates urgency vs. a "Sandbox" that waits for player initiative).
7.  **FR8**: The bot must provide a clear, comprehensive "Getting Started" guide and a `/cost` command that links to transparent cost-average data to help users understand the BYOK model before they commit.

### Non-Functional Requirements
1.  **NFR1**: Voice-based interactions should have a target roundtrip latency of under 4 seconds.
2.  **NFR2**: The system must securely handle all user-provided API keys.
3.  **NFR3**: The architecture must support future post-MVP capabilities for processing and storing user-uploaded copyrighted content on the user's local machine.
4.  **NFR4**: The configuration process for a "Hobbyist" user with their own API key should be completable in under 15 minutes.
