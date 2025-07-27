# Information Architecture (IA)

This architecture is designed around two distinct user states: a **Command State** for out-of-character management and a **Role-playing State** for in-character immersion.

### Command & State Inventory

```mermaid
graph TD
    A[User] --> B{Interaction State?};
    B --> C[Command State];
    B --> D[Role-playing State];

    subgraph C [Command State (Out-of-Character)]
        direction LR
        C1[/server-setup]
        C2[/server-setkey]
        C3[/help & /cost]
        C4[/campaign new]
        C5[/campaign continue]
        C6[/campaign end (Autosaves)]
    end

    subgraph D [Role-playing State (In-Character)]
        direction LR
        D1[Player Action (Text/Voice)] --> D2[AI Response & Autosave]
        D3[Take Long Rest (Clean Save Point)] --> D2
        D2 --> D1
    end
````

### Interaction Flow

  * **Primary Navigation:** Users interact with the bot using slash commands when in the **Command State**. The `/help` command is the primary discovery tool for these functions.
  * **Entering Role-playing State:** Using `/campaign new` or `/campaign continue` transitions the user into the immersive, **Role-playing State**.
  * **In-Character Interaction:** In this state, users interact naturally via text or voice. The system **autosaves progress** continuously. Explicit commands are not needed for gameplay.
  * **Exiting Role-playing State:** The session ends and returns to the Command State when the party takes a long rest, a natural story conclusion is reached, or a user issues a `/campaign end` command.
