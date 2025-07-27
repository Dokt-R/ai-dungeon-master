# API Specification

The communication between the Bot and Backend is defined by the following OpenAPI 3.0 contract.

```yaml
openapi: 3.0.1
info:
  title: AI DM Backend API
  version: 1.0.0
  description: API for managing campaigns, settings, and interacting with the AI Dungeon Master.
servers:
  - url: /api/v1
paths:
  /servers/{server\_id}/config:
    put:
      summary: Create or Update Server Configuration
      description: Sets the server-wide API key and play style settings.
  /campaigns:
    post:
      summary: Create a new campaign
  /campaigns/{campaign\_id}/join:
    post:
      summary: Join an existing campaign
  /campaigns/{campaign\_id}/action:
    post:
      summary: Submit a player action
  /characters/{character\_id}:
    get:
      summary: Get Character Information
```
