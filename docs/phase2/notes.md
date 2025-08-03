### **The "Character-Specific Chronicle"**

We will introduce a new architectural concept: the **"Character-Specific Chronicle."** This will be a part of our `AI Notetaker`'s responsibilities.

* **How it works:** As the `AI Notetaker` processes the main `transcript.log`, it won't just identify key events; it will also **tag actions and dialogue to the specific character who performed them**. Over time, this builds a rich, detailed profile for each character, capturing:
    * Their typical combat tactics (do they prefer to attack recklessly or hang back?).
    * Their expressed personality (are they sarcastic, brave, cautious?).
    * Their relationships with specific NPCs.
* **How it guides the AI:** When the "AI Auto-Play" is active, the AI DM will be given not just the character's static sheet but also this rich "Character Chronicle" as its primary context. This will allow it to make decisions that are not just mechanically correct, but *in character*.

### **Where We Will Document This**

## architect

...
* **`CampaignMemoryService`:** Manages the **four-tiered persistence strategy**. It is responsible for loading the 'Campaign Knowledge Base' into the graph state, appending events to the 'Campaign Chronicle', and providing access to the SQLite 'Rules Library'.
    * **(New)** This service is also responsible for building and maintaining the **"Character-Specific Chronicles,"** tagging actions and dialogue from the main transcript to individual characters to create dynamic personality profiles for the AI to use.
...

----- 
/guilds
/dm-screen
/world-engine
any missing stories?