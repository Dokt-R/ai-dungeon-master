# Core UX Principle: Explicit State Transitions

To ensure the user is always aware of when they are interacting with the AI (and thus using API tokens), the bot MUST provide explicit confirmation messages upon entering and exiting the immersive "Role-playing State."

- **On Entry (e.g., after `/campaign continue`):**
  > **Entering immersive role-playing mode. All messages from now on will be processed by the AI.**

- **On Exit (e.g., after `/campaign end`):**
  > **Exiting immersive mode. Progress has been saved. You are now in command mode.**