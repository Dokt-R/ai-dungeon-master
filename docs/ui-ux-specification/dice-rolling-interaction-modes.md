# Dice Rolling & Interaction Modes

To provide maximum flexibility, the bot will support two foundational **"Character Sheet Modes."** The host will select the mode for the campaign during `/campaign new`. This choice determines which Player Roll Modes are available.

### Foundational Setting: Character Sheet Mode

1.  **Digital Sheet Mode (Default):** Players provide a link to a public character sheet (e.g., D\&D Beyond). In this mode, the bot **knows** the character's stats, modifiers, and abilities. This enables the most powerful and automated features.
2.  **Physical Sheet Mode:** Players use their own physical or private digital sheets. The bot has **no knowledge** of the character's stats. It must trust the player to provide all information.

### DM Roll Visibility

A separate campaign-wide setting will determine if the DM's rolls are public or hidden, simulating the use of a "DM screen."

### Available Player Roll Modes (Based on Sheet Mode)

#### If in "Digital Sheet Mode":

*(The bot knows all the character's modifiers)*

  * **1. Manual (Raw d20 Roll):** The player wants to use physical dice but doesn't want to do math.
  * **2. Manual (Digital Dice):** The player wants to trigger a roll but have the bot do the math.
  * **3. Automatic (Transparent Rolls):** The bot handles everything and shows its work.
  * **4. Automatic (Hidden Rolls):** The most immersive, narrative-only mode.

#### If in "Physical Sheet Mode":

*(The bot knows nothing and must trust the player completely)*

  * **1. Manual (Player-Calculated Total):** The player does all the math and states the final total.
  * **2. Manual (Digital Dice Roller):** The player wants to use the bot as a simple calculator and must provide the full formula (e.g., `/roll 1d20+5`).
