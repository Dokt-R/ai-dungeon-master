# SRD API Specification

This document defines the API endpoints for the D&D 5.1 SRD (System Reference Document) functionality integrated into the AI Dungeon Master system.

## SRD API Endpoints

### Compliance Management

#### GET /api/v1/srd/compliance/status
Get current SRD compliance verification status and audit information.

**Response:**
```json
{
  "status": "healthy",
  "last_verification": "2025-08-22T19:30:00Z",
  "total_entities": 1500,
  "compliance_rate": 0.98,
  "recent_violations": 2
}
```

### Rules Query

#### POST /api/v1/srd/rules/query
Query the D&D 5.1 SRD database for monsters, spells, or weapons.

**Request:**
```json
{
  "query_type": "monster",
  "name": "Goblin",
  "context": "encounter",
  "filters": {
    "min_cr": 0.25,
    "max_cr": 1
  }
}
```

**Response:**
```json
{
  "query_type": "monster",
  "name": "Goblin",
  "found": true,
  "data": {
    "monster_id": 1,
    "monster_name": "Goblin",
    "armor_class": 15,
    "hit_points": "7 (2d6)",
    "strength": 8,
    "dexterity": 14,
    "constitution": 10,
    "intelligence": 10,
    "wisdom": 8,
    "charisma": 8,
    "challenge_rating": "1/4",
    "actions": "Scimitar: +4 to hit, 1d6+2 slashing damage",
    "special_abilities": "Nimble Escape: Can take Disengage or Hide as bonus action",
    "description": "A small, green humanoid with sharp features",
    "source": "D&D 5.1 SRD",
    "compliance_status": "verified",
    "last_updated": "2025-08-22T19:30:00Z"
  },
  "query_time": 0.045
}
```

### AI Response Validation

#### POST /api/v1/srd/validation/validate
Validate an AI response against SRD rules for factual accuracy.

**Request:**
```json
{
  "query": "What is the armor class of a Goblin?",
  "ai_response": "A Goblin has an armor class of 15, hit points of 7 (2d6), and uses a scimitar that deals 1d6+2 slashing damage.",
  "expected_entities": ["Goblin"],
  "validation_type": "monster"
}
```

**Response:**
```json
{
  "query": "What is the armor class of a Goblin?",
  "ai_response": "A Goblin has an armor class of 15, hit points of 7 (2d6), and uses a scimitar that deals 1d6+2 slashing damage.",
  "expected_answer": "Goblin: AC 15, HP 7 (2d6), Challenge 1/4 (25 XP)",
  "accuracy_score": 0.85,
  "issues_found": [
    "Missing challenge rating information",
    "Incomplete hit points format"
  ],
  "corrections_suggested": [
    "Include challenge rating and XP information",
    "Use complete hit points format with dice calculation"
  ],
  "validation_details": [
    "Entity 'Goblin' found and verified in SRD",
    "Armor class correctly stated",
    "Hit points format partially correct"
  ],
  "validation_date": "2025-08-22T19:30:00Z"
}
```

### Database Management

#### GET /api/v1/srd/database/stats
Get SRD database statistics and health information.

**Response:**
```json
{
  "total_monsters": 325,
  "total_spells": 367,
  "total_weapons": 78,
  "database_size": 5242880,
  "last_backup": "2025-08-22T18:00:00Z",
  "schema_version": "1.0",
  "connection_healthy": true
}
```

### Audit & Monitoring

#### GET /api/v1/srd/audit/events
Retrieve audit events for SRD data access and modifications.

**Query Parameters:**
- `start_date`: ISO datetime string
- `end_date`: ISO datetime string
- `event_type`: data_access, data_modification, compliance_check, import_operation
- `user_id`: Filter by specific user
- `entity_type`: monster, spell, weapon

**Response:**
```json
[
  {
    "event_id": "audit_20250822_193000_abc123",
    "event_type": "data_access",
    "entity_type": "monster",
    "entity_name": "Goblin",
    "user_id": "ai_agent",
    "user_role": "system",
    "timestamp": "2025-08-22T19:30:00Z",
    "details": {
      "access_type": "query",
      "entity_id": 1,
      "data_source": "D&D 5.1 SRD"
    },
    "ip_address": null,
    "user_agent": "AI Dungeon Master v1.0",
    "session_id": "session_12345"
  }
]
```

## LangGraph Tool Integration

### Tool Definitions

The SRD Tool Service provides the following LangGraph-compatible tools:

#### 1. Monster Query Tool
```json
{
  "name": "query_monster",
  "description": "Query detailed information about a D&D 5.1 SRD monster including combat statistics, abilities, and challenge rating.",
  "parameters": {
    "type": "object",
    "properties": {
      "name": {"type": "string", "description": "Name of the monster to query"},
      "include_combat_stats": {"type": "boolean", "description": "Whether to include detailed combat statistics"},
      "context": {"type": "string", "description": "Context for the query"}
    },
    "required": ["name"]
  }
}
```

#### 2. Spell Query Tool
```json
{
  "name": "query_spell",
  "description": "Query detailed information about a D&D 5.1 SRD spell including mechanics, components, and effects.",
  "parameters": {
    "type": "object",
    "properties": {
      "name": {"type": "string", "description": "Name of the spell to query"},
      "include_mechanics": {"type": "boolean", "description": "Whether to include detailed spell mechanics"},
      "context": {"type": "string", "description": "Context for the query"}
    },
    "required": ["name"]
  }
}
```

#### 3. Weapon Query Tool
```json
{
  "name": "query_weapon",
  "description": "Query detailed information about a D&D 5.1 SRD weapon including damage, properties, and combat analysis.",
  "parameters": {
    "type": "object",
    "properties": {
      "name": {"type": "string", "description": "Name of the weapon to query"},
      "include_analysis": {"type": "boolean", "description": "Whether to include weapon effectiveness analysis"},
      "context": {"type": "string", "description": "Context for the query"}
    },
    "required": ["name"]
  }
}
```

#### 4. Entity Comparison Tool
```json
{
  "name": "compare_entities",
  "description": "Compare multiple D&D 5.1 SRD entities side-by-side for analysis and decision making.",
  "parameters": {
    "type": "object",
    "properties": {
      "entity_type": {"type": "string", "enum": ["monster", "spell", "weapon"]},
      "names": {"type": "array", "items": {"type": "string"}, "description": "Names of entities to compare"},
      "comparison_focus": {"type": "string", "enum": ["combat", "roleplay", "optimization", "general"]}
    },
    "required": ["entity_type", "names"]
  }
}
```

## Performance Requirements

All SRD API endpoints are designed to meet strict performance criteria:

- **Rules Queries**: <100ms response time
- **AI Validation**: <500ms validation time
- **Tool Calls**: <100ms execution time
- **Database Operations**: <50ms for simple queries
- **Batch Operations**: <1000ms for bulk operations

## Error Handling

### Standard Error Responses

All SRD API endpoints return structured error responses:

```json
{
  "error": "Entity not found in SRD database",
  "error_code": "SRD_ENTITY_NOT_FOUND",
  "query": "NonexistentMonster",
  "query_type": "monster",
  "timestamp": "2025-08-22T19:30:00Z"
}
```

### HTTP Status Codes

- `200`: Success
- `400`: Bad Request (invalid parameters)
- `404`: Not Found (entity not in SRD)
- `422`: Validation Error (invalid data format)
- `500`: Internal Server Error
- `503`: Service Unavailable (compliance issues)

## Authentication & Authorization

SRD API endpoints use the following security model:

- **Internal API Key**: For service-to-service communication
- **Role-Based Access**: Different permission levels for different operations
- **Audit Logging**: All API access is logged for compliance
- **Rate Limiting**: Prevents abuse of SRD query endpoints

## Monitoring & Observability

The SRD API includes comprehensive monitoring:

- **Response Times**: Tracked for all endpoints
- **Error Rates**: Monitored by endpoint and error type
- **Usage Analytics**: Query patterns and frequency
- **Compliance Metrics**: Verification success rates
- **Performance Dashboards**: Real-time monitoring views

This API specification ensures the SRD functionality is properly integrated into the AI Dungeon Master system while maintaining high performance, security, and compliance standards.