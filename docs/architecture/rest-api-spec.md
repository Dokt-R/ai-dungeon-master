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