openapi: 3.0.1
info:
  title: AI DM Backend API
  version: 1.0.0
  description: API for managing campaigns, settings, and interacting with the AI Dungeon Master.

servers:
  - url: /api/v1

paths:
  /servers/{server_id}/config:
    put:
      summary: Create or Update Server Configuration
      description: Sets the server-wide API key and play style settings. Used by /server-setkey.
      parameters:
        - in: path
          name: server_id
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ServerConfig'
      responses:
        '200':
          description: Configuration Updated
        '201':
          description: Configuration Created

  /campaigns:
    post:
      summary: Create a new campaign
      description: Initializes a new campaign on a server with a memorable name.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                server_id:
                  type: string
                campaign_name:
                  type: string
                host_discord_id:
                  type: string
      responses:
        '201':
          description: Campaign Created

  /campaigns/{campaign_id}/join:
    post:
      summary: Join an existing campaign
      description: Allows a player to join a campaign with their character.
      parameters:
        - in: path
          name: campaign_id
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                player_discord_id:
                  type: string
                character_sheet_url:
                  type: string
      responses:
        '200':
          description: Player Joined

  /campaigns/{campaign_id}/action:
    post:
      summary: Submit a player action
      description: Sends a player's text or voice input to the AI for processing.
      parameters:
        - in: path
          name: campaign_id
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                player_discord_id:
                  type: string
                action_text:
                  type: string
      responses:
        '200':
          description: AI Narrative Response
          content:
            application/json:
              schema:
                type: object
                properties:
                  narrative:
                    type: string

  /characters/{character_id}:
    get:
      summary: Get Character Information
      description: Retrieves the data for a specific character, used by the /sheet command.
      parameters:
        - in: path
          name: character_id
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Character Data
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PlayerCharacter'

components:
  schemas:
    ServerConfig:
      type: object
      properties:
        api_key:
          type: string
          description: The user-provided API key for the AI provider.
        dm_roll_visibility:
          type: string
          enum: [public, hidden]
        player_roll_mode:
          type: string
          enum: [manual_physical_total, manual_physical_raw, manual_digital, auto_visible, auto_hidden]
        character_sheet_mode:
          type: string
          enum: [digital_sheet, physical_sheet]
    PlayerCharacter:
      type: object
      properties:
        character_id:
          type: string
        player_discord_id:
          type: string
        campaign_id:
          type: string
        name:
          type: string
        character_sheet_url:
          type: string

          
# Player and Character Management Endpoints

## /players/join_campaign (POST)
- **Description:** Join an existing campaign as a player, optionally associating a character.
- **Request Body:**
  ```json
  {
    "server_id": "string",
    "campaign_name": "string",
    "player_id": "string",
    "character_name": "string (optional)",
    "dnd_beyond_url": "string (optional)"
  }
  ```
- **Response:**
  ```json
  {
    "message": "Campaign joined successfully.",
    "result": {
      "campaign_name": "string",
      "player_id": "string",
      "character_id": "int or null",
      "status": "joined"
    }
  }
  ```
- **Errors:** 400 (ValidationError), 404 (NotFoundError)

## /players/end_campaign (POST)
- **Description:** Temporarily exit a campaign, setting the player's status to 'cmd' (command state).
- **Request Body:**
  ```json
  {
    "server_id": "string",
    "campaign_name": "string",
    "player_id": "string"
  }
  ```
- **Response:**
  ```json
  {
    "message": "Campaign exited successfully.",
    "narrative": "string or null"
  }
  ```
- **Errors:** 400 (ValidationError), 404 (NotFoundError)

## /players/leave_campaign (POST)
- **Description:** Remove a player from a campaign.
- **Request Body:**
  ```json
  {
    "server_id": "string",
    "campaign_name": "string",
    "player_id": "string"
  }
  ```
- **Response:**
  ```json
  {
    "message": "Left campaign successfully.",
    "result": {
      "campaign_name": "string",
      "player_id": "string",
      "status": "left"
    }
  }
  ```
- **Errors:** 400 (ValidationError), 404 (NotFoundError)

## /players/status/{player_id} (GET)
- **Description:** Retrieve a summary of the player's campaigns, characters, and current status.
- **Response:**
  ```json
  {
    "player_status": {
      "player_id": "string",
      "username": "string",
      "last_active_campaign": "int or null",
      "campaigns": [
        {"campaign_name": "string", "player_status": "string"}
      ],
      "characters": [
        {"character_id": "int", "name": "string", "dnd_beyond_url": "string or null"}
      ]
    }
  }
  ```
- **Errors:** 404 (NotFoundError)

---

## /characters/add (POST)
- **Description:** Add a new character for a player.
- **Request Body:**
  ```json
  {
    "player_id": "string",
    "name": "string",
    "dnd_beyond_url": "string (optional)"
  }
  ```
- **Response:**
  ```json
  {
    "character_id": "int"
  }
  ```
- **Errors:** 400 (ValidationError), 404 (NotFoundError)

## /characters/update (POST)
- **Description:** Update an existing character's name and/or D&D Beyond URL.
- **Request Body:**
  ```json
  {
    "character_id": "int",
    "name": "string (optional)",
    "dnd_beyond_url": "string (optional)"
  }
  ```
- **Response:**
  ```json
  {
    "success": true
  }
  ```
- **Errors:** 400 (ValidationError), 404 (NotFoundError)

## /characters/remove (POST)
- **Description:** Remove a character by character_id.
- **Request Body:**
  ```json
  {
    "character_id": "int"
  }
  ```
- **Response:**
  ```json
  {
    "success": true
  }
  ```
- **Errors:** 404 (NotFoundError)

## /characters/list (POST)
- **Description:** Retrieve all characters for a given player.
- **Request Body:**
  ```json
  {
    "player_id": "string"
  }
  ```
- **Response:**
  ```json
  {
    "characters": [
      {"character_id": "int", "name": "string", "dnd_beyond_url": "string or null"}
    ]
  }
  ```
- **Errors:** 404 (NotFoundError)

---