# Bot Invite Instructions
1. Go to the Discord Developer Portal.
2. Navigate to your application and select the "OAuth2" tab.
3. Under "Scopes", select the `bot` checkbox.
4. Under "Bot Permissions", select the following permissions:
   - Read Messages/View Channels
   - Send Messages
   - Send Messages in Threads
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

**Note:**
If the bot does not respond to commands in servers, ensure that the "Message Content Intent" is enabled in the Discord Developer Portal for your bot, and that the bot has the required permissions in your server.
