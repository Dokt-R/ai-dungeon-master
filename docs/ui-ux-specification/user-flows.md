# User Flows

### Flow: Managing a Campaign Session

**User Goal:** To be able to start, play, take a break, and seamlessly resume a campaign in an immersive way.
**Entry Points:** `/campaign new` or `/campaign continue` commands.
**Success Criteria:** The user can end and resume a session without losing any progress and without feeling like their immersion was broken by technical commands.

#### Flow Diagram

```mermaid
sequenceDiagram
    participant Player
    participant Bot
    participant AI_Backend as AI Backend

    Player->>Bot: /campaign continue
    Bot->>AI_Backend: Load last clean save point
    AI_Backend-->>Bot: Narrative: "Welcome back! You are rested..."
    Bot-->>Player: Narrative: "Welcome back! You are rested..."

    loop Gameplay Loop
        Player->>Bot: "I attack the dragon!" (Action)
        Bot->>AI_Backend: Process Action + Autosave
        AI_Backend-->>Bot: Narrative Response
        Bot-->>Player: "You swing your sword..."
    end

    Player->>Bot: "We make camp for the night." (Triggers Clean Save)
    Bot->>AI_Backend: Initiate Clean Save Point
    AI_Backend-->>Bot: Narrative + Prompt: "You set up camp... [Progress Saved]. Do you wish to continue playing?"
    Bot-->>Player: "You set up camp... [Progress Saved]. Do you wish to continue playing?"

    alt Player wishes to stop
        Player->>Bot: "Let's end for now."
        Bot-->>Player: "Understood. Your adventure awaits your return! (Type /campaign continue to resume)"
        Note over Bot: Bot returns to Command State
    else Player wishes to continue
        Player->>Bot: "Yes, let's keep going."
        Bot->>AI_Backend: Continue narrative
        AI_Backend-->>Bot: New Narrative Prompt
        Bot-->>Player: New Narrative Prompt
    end
```

**Edge Cases & Error Handling:**

  * If the user is disconnected unexpectedly, the system will rely on the last **Autosave**. Upon using `/campaign continue`, the user will be restored to their last known action.

### Flow: New Campaign & Character Creation

**User Goal:** To easily start a brand new adventure and bring my D\&D character into the game world.
**Entry Points:** The `/campaign new` command.
**Success Criteria:** A new user can successfully start a campaign and register their character with the bot in a single, guided interaction, ready for gameplay.

#### Flow Diagram

```mermaid
sequenceDiagram
    participant Player
    participant Bot
    participant AI_Backend as AI Backend

    Player->>Bot: /campaign new "Shadows over Phandalin"
    Bot-->>Player: "Campaign 'Shadows over Phandalin' created! Others can join by typing: /campaign join \"Shadows over Phandalin\""
    Bot-->>Player: "Next, let's set up your character. Will you be using a Digital Sheet (link from D&D Beyond etc.) or a Physical Sheet?"
```

#### Notes:

  * The character setup process will depend on the "Character Sheet Mode" chosen for the campaign (see Dice Rolling & Interaction Modes section).

### Flow: Forming a Campaign Party

**User Goal:** As a server owner, to create a campaign, and as a player, to easily join it with my character using a memorable name.
**Entry Points:** `/campaign new [name]`, `/campaign join [name]`
**Success Criteria:** A group of 2-5 players can successfully form a party and be ready to start a campaign together.

#### Flow Diagram

```mermaid
sequenceDiagram
    participant Host as Host/Server Owner
    participant Player2 as Player 2
    participant Bot

    Host->>Bot: /campaign new "Shadows over Phandalin"
    Bot-->>Host: "Campaign 'Shadows over Phandalin' created! Others can join by typing: /campaign join \"Shadows over Phandalin\""
    
    Host->>Bot: /campaign join "Shadows over Phandalin"
    Bot-->>Host: "Great! Please provide a link to your character sheet or let me know you're using a physical one."
    Host->>Bot: "[link to host's sheet]"
    Bot-->>Host: "Welcome to the party, [Host's Character]!"

    Player2->>Bot: /campaign join "Shadows over Phandalin"
    Bot-->>Player2: "Great! Please provide a link to your character sheet or let me know you're using a physical one."
    Player2->>Bot: "[link to player2's sheet]"
    Bot-->>Player2: "Welcome to the party, [Player2's Character]!"
```
