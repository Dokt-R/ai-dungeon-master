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
      description: Sets the server-wide API key and play style settings.
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

  /campaigns/new:
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
                owner_id:
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
      description: Retrieves the data for a specific character.
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

  /players/join_campaign:
    post:
      summary: Join an existing campaign as a player, optionally associating a character.
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
                player_id:
                  type: string
                character_name:
                  type: string
                  nullable: true
                character_url:
                  type: string
                  nullable: true
      responses:
        '200':
          description: Campaign joined successfully.
          content:
            application/json:
              schema:
                type: object
                properties:
                  message:
                    type: string
                  result:
                    type: object
                    properties:
                      campaign_name:
                        type: string
                      player_id:
                        type: string
                      character_id:
                        type: integer
                        nullable: true
                      status:
                        type: string
        '400':
          description: ValidationError
        '404':
          description: NotFoundError

  /players/end_campaign:
    post:
      summary: Temporarily exit a campaign, setting the player's status to 'cmd' (command state).
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
                player_id:
                  type: string
      responses:
        '200':
          description: Campaign exited successfully.
          content:
            application/json:
              schema:
                type: object
                properties:
                  message:
                    type: string
                  narrative:
                    type: string
                    nullable: true
        '400':
          description: ValidationError
        '404':
          description: NotFoundError

  /players/remove_campaign:
    post:
      summary: Remove a player from a campaign.
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
                player_id:
                  type: string
      responses:
        '200':
          description: Left campaign successfully.
          content:
            application/json:
              schema:
                type: object
                properties:
                  message:
                    type: string
                  result:
                    type: object
                    properties:
                      campaign_name:
                        type: string
                      player_id:
                        type: string
                      status:
                        type: string
        '400':
          description: ValidationError
        '404':
          description: NotFoundError

  /players/status/{player_id}:
    get:
      summary: Retrieve a summary of the player's campaigns, characters, and current status.
      parameters:
        - in: path
          name: player_id
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Player status summary.
          content:
            application/json:
              schema:
                type: object
                properties:
                  player_status:
                    type: object
                    properties:
                      player_id:
                        type: string
                      username:
                        type: string
                      last_active_campaign:
                        type: integer
                        nullable: true
                      campaigns:
                        type: array
                        items:
                          type: object
                          properties:
                            campaign_name:
                              type: string
                            player_status:
                              type: string
                      characters:
                        type: array
                        items:
                          type: object
                          properties:
                            character_id:
                              type: integer
                            name:
                              type: string
                            character_url:
                              type: string
                              nullable: true
        '404':
          description: NotFoundError

  /characters/add:
    post:
      summary: Add a new character for a player.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                player_id:
                  type: string
                name:
                  type: string
                character_url:
                  type: string
                  nullable: true
      responses:
        '200':
          description: Character added successfully.
          content:
            application/json:
              schema:
                type: object
                properties:
                  character_id:
                    type: integer
        '400':
          description: ValidationError
        '404':
          description: NotFoundError

  /characters/update:
    post:
      summary: Update an existing character's name and/or D&D Beyond URL.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                character_id:
                  type: integer
                name:
                  type: string
                  nullable: true
                character_url:
                  type: string
                  nullable: true
      responses:
        '200':
          description: Character updated successfully.
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
        '400':
          description: ValidationError
        '404':
          description: NotFoundError

  /characters/remove:
    post:
      summary: Remove a character by character_id.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                character_id:
                  type: integer
      responses:
        '200':
          description: Character removed successfully.
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
        '404':
          description: NotFoundError

  /characters/list:
    post:
      summary: Retrieve all characters for a given player.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                player_id:
                  type: string
      responses:
        '200':
          description: List of characters.
          content:
            application/json:
              schema:
                type: object
                properties:
                  characters:
                    type: array
                    items:
                      type: object
                      properties:
                        character_id:
                          type: integer
                        name:
                          type: string
                        character_url:
                          type: string
                          nullable: true
        '404':
          description: NotFoundError

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