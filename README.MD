# Bot Invite Instructions
1. Go to the Discord Developer Portal.
2. Navigate to your application and select the "OAuth2" tab.
3. Under "Scopes", select the `bot` checkbox.
4. Under "Bot Permissions", select the following permissions:
   - View Channels
   - Send Messages
   - Send Messages in Threads
   - Embed Links
   - Read Message History
   - Use Slash Commands
   - (Optional, for advanced features: Manage Messages, Embed Links, Attach Files, etc.)
5. In the "Bot" section of the Developer Portal, under "Privileged Gateway Intents", enable the **Message Content Intent**. This is required for the bot to respond to commands in servers.
6. Click Reset Token if necessary and note the token somewhere for now.
7. Copy the generated OAuth2 URL and use it to invite the bot to your server. This can be easily done by pasting the url in your server.

# Usage Instructions
- To start the bot, ensure you have created a `.env` file in the root of your project with the following line:
  ```
  DISCORD_BOT_TOKEN=your_bot_token_here
  ```
  Replace `your_bot_token_here` with your actual bot token.
- Run the bot using the command:
  ```bash
  python packages/bot/bot.py
  ```
- Use the `/ping` command in any channel where the bot is present to test its functionality.

# Server Key Onboarding Command Flow

## Commands

- `/server-setup`: Explains the shared API key model and how to submit a key. Only users with "Administrator" or "Manage Server" permissions can run this command.
- `/server-setkey [API_KEY]`: Allows an admin to submit the server's shared API key. Only users with "Administrator" or "Manage Server" permissions can run this command. The key is securely stored and never shown to other users.

## Security Considerations

- API keys are encrypted at rest using Fernet symmetric encryption.
- Keys are never exposed in logs or non-ephemeral messages.
- All key submission and confirmation messages are sent as ephemeral responses, ensuring only the submitting admin can view them.
- Only users with the required permissions can submit or update the server API key.
- All secrets are managed via environment variables and never hardcoded.


# Storage and Retrieval Process
- The application utilizes a database to store user data, bot configurations, and other relevant information.
- Data is stored in a structured format, following the defined database schema located in `packages/backend/database_schema_extension.sql`.
- The retrieval process involves querying the database using the appropriate service methods defined in the application, ensuring efficient access to the stored data.
- For more details on the database schema and how to interact with it, refer to the `database_schema_extension.sql` file.

**Note**
If the bot does not respond to commands in servers, ensure that the "Message Content Intent" is enabled in the Discord Developer Portal for your bot, and that the bot has the required permissions in your server.
