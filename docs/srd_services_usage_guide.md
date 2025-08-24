# SRD Services Usage Guide

## Overview

The SRD (System Reference Document) Services provide comprehensive access to D&D 5.1 rules, monsters, spells, weapons, and other game content. This collection includes multiple specialized services for managing SRD compliance, data access, validation, and tool integration.

### Purpose
- Centralized access to D&D 5.1 SRD data
- Compliance verification for content licensing
- AI agent integration through LangGraph tools
- Data import and validation from external sources
- Audit trail for SRD data access and modifications
- Migration support for SRD data updates

## Key Components

### Core SRD Services

#### `SRDDatabaseManager` (`packages/backend/components/srd_database_manager.py`)
Central database manager for all SRD data.

**Key Methods:**
- `get_monster_by_name(name)` - Retrieve monster by name
- `get_spells_by_level(level)` - Get spells by level
- `get_weapons_by_category(category)` - Get weapons by category
- `create_monster(monster, user)` - Create new monster entry
- `update_monster(monster_id, updates, user)` - Update monster
- `delete_monster(monster_id, user)` - Delete monster
- `get_database_stats()` - Get database statistics
- `create_backup(name)` - Create database backup

#### `SRDComplianceService` (`packages/backend/components/srd_compliance_service.py`)
Manages SRD compliance and licensing verification.

**Key Methods:**
- `verify_data_compliance(data, data_type, operation)` - Verify data compliance
- `get_compliance_requirements(data_type)` - Get compliance requirements
- `check_licensing_status(data)` - Check licensing status
- `generate_compliance_report()` - Generate compliance report

#### `SrdAuditService` (`packages/backend/components/srd_audit_service.py`)
Provides audit trail functionality for SRD data access and modifications.

**Key Methods:**
- `log_data_access(data, service, user, operation)` - Log data access
- `log_data_modification(data, service, user, operation, changes)` - Log modifications
- `get_audit_trail(data_id, data_type)` - Get audit trail
- `generate_audit_report(time_range)` - Generate audit report

#### `SRDToolService` (`packages/backend/components/srd_tool_service.py`)
LangGraph-compatible tools for AI agent integration.

**Key Methods:**
- `get_monster_info(name)` - Get monster information tool
- `get_spell_info(name)` - Get spell information tool
- `get_weapon_info(name)` - Get weapon information tool
- `search_content(query)` - Search SRD content tool

#### `SRDDataImportService` (`packages/backend/components/srd_data_import_service.py`)
Handles importing SRD data from external sources.

**Key Methods:**
- `import_data(data, data_type, user)` - Import data
- `validate_import_data(data, data_type)` - Validate import data
- `get_import_status(import_id)` - Get import status
- `rollback_import(import_id, user)` - Rollback import

#### `SRDDataVerificationService` (`packages/backend/components/srd_data_verification_service.py`)
Verifies integrity and accuracy of SRD data.

**Key Methods:**
- `verify_monster_data(monster)` - Verify monster data
- `verify_spell_data(spell)` - Verify spell data
- `verify_weapon_data(weapon)` - Verify weapon data
- `generate_verification_hash(data)` - Generate verification hash

#### `SRDMigrationService` (`packages/backend/components/srd_migration_service.py`)
Manages SRD data migrations and updates.

**Key Methods:**
- `create_migration(name, description, user)` - Create migration
- `execute_migration(migration_id)` - Execute migration
- `rollback_migration(migration_id)` - Rollback migration
- `get_migration_history()` - Get migration history

## Dependencies

### Internal Dependencies
- `sqlite3` - Database operations
- `packages.shared.logging_config` - Structured logging
- `packages.shared.models` - Data models
- `packages.backend.components.rules_engine` - Rules integration

### External Dependencies
- `dataclasses` - Data structure definitions
- `datetime` - Timestamp handling
- `hashlib` - Hash generation
- `json` - Data serialization

## Configuration

### Database Configuration
```python
# Default database path
database_path = "data/srd_database.sqlite"

# Custom configuration
srd_database_manager = SRDDatabaseManager(
    database_path="custom/path/srd.db",
    enable_audit=True,
    backup_enabled=True
)
```

### Environment Variables
```bash
# Optional configuration
export SRD_DATABASE_PATH="data/srd_database.sqlite"
export SRD_AUDIT_LOG_PATH="data/audit/srd_audit.log"
export SRD_COMPLIANCE_DB_PATH="data/srd_compliance.db"
export SRD_BACKUP_RETENTION_DAYS="30"
```

## Usage Examples

### Basic Data Access

```python
from packages.backend.components.srd_database_manager import srd_database_manager

# Get monster by name
monster = srd_database_manager.get_monster_by_name("goblin")
if monster:
    print(f"Monster: {monster.monster_name}")
    print(f"Armor Class: {monster.armor_class}")
    print(f"Hit Points: {monster.hit_points}")

# Get spells by level
cantrips = srd_database_manager.get_spells_by_level(0)
for spell in cantrips:
    print(f"Cantrip: {spell.spell_name}")

# Get weapons by category
simple_weapons = srd_database_manager.get_weapons_by_category("Simple Melee Weapons")
for weapon in simple_weapons:
    print(f"Weapon: {weapon.weapon_name}, Damage: {weapon.damage}")
```

### Compliance Verification

```python
from packages.backend.components.srd_compliance_service import srd_compliance_service
from packages.shared.models import DataSource, SRDCompliance

# Check data compliance
monster = srd_database_manager.get_monster_by_name("dragon")

compliance_result = srd_compliance_service.verify_data_compliance(
    monster, "monster", "user_access"
)

if compliance_result.is_compliant:
    print("Data is SRD compliant")
else:
    print("Compliance issues:")
    for issue in compliance_result.issues:
        print(f"  - {issue}")
```

### AI Agent Integration

```python
from packages.backend.components.srd_tool_service import srd_tool_service

# Get monster info for AI agent
monster_info = await srd_tool_service.get_monster_info("beholder")

# Get spell info for AI agent
spell_info = await srd_tool_service.get_spell_info("fireball")

# Search SRD content
search_results = await srd_tool_service.search_content("fire damage")
```

### Data Import

```python
from packages.backend.components.srd_data_import_service import srd_data_import_service

# Import monster data
monster_data = {
    "monster_name": "Custom Monster",
    "armor_class": 15,
    "hit_points": "45 (7d8 + 14)",
    "strength": 16,
    "dexterity": 12,
    "constitution": 14,
    "intelligence": 8,
    "wisdom": 10,
    "charisma": 8,
    "challenge_rating": 2.0,
    "description": "A custom monster for the campaign"
}

import_result = await srd_data_import_service.import_data(
    monster_data, "monster", "dm_user"
)

if import_result.success:
    print(f"Imported {import_result.records_processed} monsters")
else:
    print("Import failed:", import_result.errors)
```

### Audit Trail

```python
from packages.backend.components.srd_audit_service import srd_audit_service

# Log data access
monster = srd_database_manager.get_monster_by_name("goblin")

srd_audit_service.log_data_access(
    data=monster,
    service="ai_agent",
    user="ai_system",
    operation="monster_lookup"
)

# Get audit trail
audit_trail = srd_audit_service.get_audit_trail(monster.monster_id, "monster")

for entry in audit_trail:
    print(f"{entry.timestamp}: {entry.operation} by {entry.user}")
```

## Integration Points

### With AI Validation Service

```python
# packages/backend/components/ai_validation_service.py
from packages.backend.components.srd_database_manager import srd_database_manager
from packages.backend.components.srd_tool_service import srd_tool_service

class AIValidationService:
    """AI validation with SRD integration."""

    async def _validate_entity_mention(self, entity_name: str, ai_response: str):
        """Validate entity mentions against SRD."""

        # Try different entity types
        for entity_type in ["monster", "spell", "weapon"]:
            try:
                if entity_type == "monster":
                    data = srd_database_manager.get_monster_by_name(entity_name)
                elif entity_type == "spell":
                    data = srd_database_manager.get_spell_by_name(entity_name)
                elif entity_type == "weapon":
                    data = srd_database_manager.get_weapon_by_name(entity_name)

                if data:
                    return await self._validate_against_srd_data(
                        entity_name, ai_response, data, entity_type
                    )
            except Exception as e:
                logger.error(f"SRD lookup failed for {entity_name}: {e}")

        # Entity not found in SRD
        return {
            "is_accurate": False,
            "issues": [f"Entity '{entity_name}' not found in official SRD"],
            "corrections": [f"Use official SRD data or mark as custom content"]
        }
```

### With Rules Engine

```python
# packages/backend/components/rules_engine.py
from packages.backend.components.srd_database_manager import srd_database_manager
from packages.backend.components.srd_compliance_service import srd_compliance_service
from packages.backend.components.srd_audit_service import srd_audit_service

class RulesEngine:
    """Rules engine with SRD integration."""

    async def query_monster(self, query: MonsterQuery) -> QueryResult:
        """Query monster data with compliance and audit."""

        # Get monster from database
        monster = srd_database_manager.get_monster_by_name(query.name)

        if not monster:
            return QueryResult(found=False, data=None)

        # Verify compliance
        compliance_result = srd_compliance_service.verify_data_compliance(
            monster, "monster", "rules_engine_query"
        )

        if not compliance_result.is_compliant:
            logger.warning(f"Monster {query.name} has compliance issues")

        # Log audit event
        srd_audit_service.log_data_access(
            data=monster,
            service="rules_engine",
            user=query.user or "system",
            operation="monster_query"
        )

        return QueryResult(
            found=True,
            data=monster,
            compliance_status=compliance_result
        )
```

### With Memory Service

```python
# packages/backend/components/memory_service.py
from packages.backend.components.srd_compliance_service import srd_compliance_service

class MemoryService:
    """Memory service with SRD compliance."""

    async def store_game_content(self, content: str, content_type: str, user: str):
        """Store game content with compliance verification."""

        # Parse content for SRD entities
        entities = self._extract_srd_entities(content)

        # Verify compliance for each entity
        compliance_issues = []
        for entity in entities:
            if hasattr(entity, 'srd_compliance'):
                compliance_result = srd_compliance_service.verify_data_compliance(
                    entity, content_type, "memory_storage"
                )

                if not compliance_result.is_compliant:
                    compliance_issues.extend(compliance_result.issues)

        # Store with compliance metadata
        memory_entry = {
            "content": content,
            "content_type": content_type,
            "user": user,
            "timestamp": datetime.utcnow(),
            "compliance_status": "compliant" if not compliance_issues else "issues",
            "compliance_issues": compliance_issues
        }

        return await self._store_memory(memory_entry)
```

### With Dungeon Master Agent

```python
# packages/backend/agents/dm_graph.py
from packages.backend.components.srd_tool_service import srd_tool_service

class DungeonMasterAgent:
    """Dungeon master with SRD tools integration."""

    def __init__(self):
        self.srd_tools = srd_tool_service

    async def generate_monster_encounter(self, monster_name: str, difficulty: str):
        """Generate encounter using SRD monster data."""

        # Get official monster data
        monster_info = await self.srd_tools.get_monster_info(monster_name)

        if not monster_info.found:
            return f"Monster '{monster_name}' not found in SRD"

        # Generate encounter description
        prompt = f"""
        Create an encounter with {monster_name} for a {difficulty} difficulty group.

        Official Stats:
        - Armor Class: {monster_info.data.armor_class}
        - Hit Points: {monster_info.data.hit_points}
        - Challenge Rating: {monster_info.data.challenge_rating}

        Generate an engaging encounter description that incorporates these official stats.
        """

        return await self.ai_client.generate_text(prompt)

    async def explain_spell_mechanics(self, spell_name: str):
        """Explain spell using official SRD data."""

        spell_info = await self.srd_tools.get_spell_info(spell_name)

        if not spell_info.found:
            return f"Spell '{spell_name}' not found in SRD"

        prompt = f"""
        Explain the mechanics of {spell_name} based on official D&D 5.1 SRD:

        Official Data:
        - Level: {spell_info.data.level}
        - Casting Time: {spell_info.data.casting_time}
        - Range: {spell_info.data.range}
        - Duration: {spell_info.data.duration}
        - Components: {spell_info.data.components}

        Provide a clear, rules-accurate explanation.
        """

        return await self.ai_client.generate_text(prompt)
```

## Error Handling

### Database Connection Issues

```python
# Handle database connection failures
async def safe_srd_query(query_func, *args, **kwargs):
    """Execute SRD query with error handling."""
    try:
        return await query_func(*args, **kwargs)
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        # Retry logic
        await asyncio.sleep(1)
        try:
            return await query_func(*args, **kwargs)
        except sqlite3.Error as e2:
            logger.error(f"Database retry failed: {e2}")
            raise SRDDatabaseError(f"Database operation failed: {e2}")
    except Exception as e:
        logger.error(f"SRD query error: {e}")
        raise
```

### Compliance Verification Failures

```python
# Handle compliance verification errors
async def verify_with_fallback(data, data_type: str, operation: str):
    """Verify compliance with fallback handling."""
    try:
        return await srd_compliance_service.verify_data_compliance(
            data, data_type, operation
        )
    except Exception as e:
        logger.warning(f"Compliance verification failed: {e}")

        # Fallback: assume compliant but log issue
        return ComplianceResult(
            is_compliant=True,
            issues=[f"Compliance check failed: {e}"],
            warnings=["Unable to verify compliance - manual review recommended"],
            verification_method="fallback"
        )
```

### Import Failure Handling

```python
# Handle data import failures
async def safe_import_data(data, data_type: str, user: str):
    """Import data with proper error handling."""
    try:
        # Validate data first
        validation_result = await srd_data_import_service.validate_import_data(
            data, data_type
        )

        if not validation_result.is_valid:
            return ImportResult(
                success=False,
                errors=validation_result.errors,
                records_processed=0
            )

        # Attempt import
        import_result = await srd_data_import_service.import_data(
            data, data_type, user
        )

        return import_result

    except Exception as e:
        logger.error(f"Data import failed: {e}")

        # Try to rollback if partial import occurred
        try:
            if 'import_id' in locals():
                await srd_data_import_service.rollback_import(import_id, user)
        except Exception as rollback_error:
            logger.error(f"Rollback failed: {rollback_error}")

        return ImportResult(
            success=False,
            errors=[f"Import failed: {e}"],
            records_processed=0
        )
```

## Performance Considerations

### Database Optimization

```python
# Use database connection pooling
class SRDDatabaseManager:
    """Optimized database manager with connection pooling."""

    def __init__(self, max_connections: int = 5):
        self.max_connections = max_connections
        self._connection_pool = []
        self._init_connection_pool()

    def _init_connection_pool(self):
        """Initialize database connection pool."""
        for _ in range(self.max_connections):
            conn = sqlite3.connect(self.database_path)
            self._connection_pool.append(conn)

    def get_connection(self):
        """Get database connection from pool."""
        return self._connection_pool.pop()

    def return_connection(self, conn):
        """Return connection to pool."""
        if len(self._connection_pool) < self.max_connections:
            self._connection_pool.append(conn)
        else:
            conn.close()
```

### Caching Strategy

```python
# Implement caching for frequently accessed data
from functools import lru_cache

class SRDCache:
    """Cache for SRD data access."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size

    @lru_cache(maxsize=500)
    def get_monster_cache(self, name: str):
        """Cache monster lookups."""
        return srd_database_manager.get_monster_by_name(name)

    @lru_cache(maxsize=200)
    def get_spell_cache(self, name: str):
        """Cache spell lookups."""
        return srd_database_manager.get_spell_by_name(name)

    def clear_cache(self):
        """Clear all caches."""
        self.get_monster_cache.cache_clear()
        self.get_spell_cache.cache_clear()
```

### Batch Operations

```python
# Implement batch operations for efficiency
async def batch_get_monsters(names: List[str]) -> List[Monster]:
    """Get multiple monsters efficiently."""
    tasks = []
    for name in names:
        task = asyncio.create_task(
            srd_database_manager.get_monster_by_name(name)
        )
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter out exceptions and return valid results
    monsters = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning(f"Monster lookup failed: {result}")
        else:
            monsters.append(result)

    return monsters
```

## Best Practices

### 1. Data Access Patterns

```python
# Use appropriate access patterns for different scenarios
class SRDDataAccessPatterns:
    """Recommended data access patterns."""

    @staticmethod
    async def get_for_ai_agent(entity_name: str, entity_type: str):
        """Get data optimized for AI agent usage."""
        # Use tools service for AI integration
        if entity_type == "monster":
            return await srd_tool_service.get_monster_info(entity_name)
        elif entity_type == "spell":
            return await srd_tool_service.get_spell_info(entity_name)
        elif entity_type == "weapon":
            return await srd_tool_service.get_weapon_info(entity_name)

    @staticmethod
    async def get_for_rules_engine(entity_name: str, entity_type: str):
        """Get data optimized for rules engine."""
        # Use database manager for rules processing
        if entity_type == "monster":
            return srd_database_manager.get_monster_by_name(entity_name)
        elif entity_type == "spell":
            return srd_database_manager.get_spell_by_name(entity_name)
        elif entity_type == "weapon":
            return srd_database_manager.get_weapon_by_name(entity_name)

    @staticmethod
    async def get_for_validation(entity_name: str, entity_type: str):
        """Get data optimized for validation."""
        # Include compliance and audit data
        data = await SRDDataAccessPatterns.get_for_rules_engine(entity_name, entity_type)

        if data:
            # Add compliance information
            compliance = await srd_compliance_service.verify_data_compliance(
                data, entity_type, "validation_lookup"
            )
            data.compliance_status = compliance

        return data
```

### 2. Compliance Management

```python
# Implement comprehensive compliance checking
async def ensure_srd_compliance(data, data_type: str, operation: str):
    """Ensure data complies with SRD requirements."""

    # Check basic compliance
    compliance_result = await srd_compliance_service.verify_data_compliance(
        data, data_type, operation
    )

    if not compliance_result.is_compliant:
        # Log compliance issues
        for issue in compliance_result.issues:
            logger.warning(f"Compliance issue: {issue}")

        # Check if operation can proceed with issues
        if operation in ["read", "query"]:
            logger.info("Proceeding with read operation despite compliance issues")
        else:
            raise SRDComplianceError(
                f"Operation blocked due to compliance issues: {compliance_result.issues}"
            )

    # Log compliance check
    srd_audit_service.log_data_access(
        data=data,
        service="compliance_checker",
        user="system",
        operation=f"compliance_check_{operation}"
    )

    return compliance_result
```

### 3. Audit Trail Management

```python
# Implement comprehensive audit logging
class SRDAuditManager:
    """Manage SRD audit trail."""

    @staticmethod
    async def log_data_operation(data, operation: str, user: str, service: str):
        """Log data operation with full context."""

        # Prepare audit data
        audit_data = {
            "data_id": getattr(data, 'id', None),
            "data_type": type(data).__name__,
            "data_name": getattr(data, 'name', None),
            "operation": operation,
            "user": user,
            "service": service,
            "timestamp": datetime.utcnow(),
            "data_hash": SRDDataVerificationService.generate_verification_hash(data)
        }

        # Log to audit service
        await srd_audit_service.log_data_access(
            data=data,
            service=service,
            user=user,
            operation=operation
        )

        # Additional structured logging
        logger.info(
            "srd_data_operation",
            data_id=audit_data["data_id"],
            data_type=audit_data["data_type"],
            operation=operation,
            user=user,
            service=service
        )

    @staticmethod
    async def generate_operation_report(time_range: tuple):
        """Generate report of operations in time range."""
        start_time, end_time = time_range

        audit_entries = await srd_audit_service.get_audit_entries(
            start_time=start_time,
            end_time=end_time
        )

        report = {
            "time_range": {"start": start_time, "end": end_time},
            "total_operations": len(audit_entries),
            "operations_by_type": {},
            "operations_by_user": {},
            "operations_by_service": {}
        }

        for entry in audit_entries:
            # Count by operation type
            if entry.operation not in report["operations_by_type"]:
                report["operations_by_type"][entry.operation] = 0
            report["operations_by_type"][entry.operation] += 1

            # Count by user
            if entry.user not in report["operations_by_user"]:
                report["operations_by_user"][entry.user] = 0
            report["operations_by_user"][entry.user] += 1

            # Count by service
            if entry.service not in report["operations_by_service"]:
                report["operations_by_service"][entry.service] = 0
            report["operations_by_service"][entry.service] += 1

        return report
```

### 4. Data Validation

```python
# Implement comprehensive data validation
async def validate_srd_data(data, data_type: str):
    """Validate SRD data integrity."""

    validation_errors = []

    # Type-specific validation
    if data_type == "monster":
        validation_errors.extend(await SRDDataVerificationService.verify_monster_data(data))
    elif data_type == "spell":
        validation_errors.extend(await SRDDataVerificationService.verify_spell_data(data))
    elif data_type == "weapon":
        validation_errors.extend(await SRDDataVerificationService.verify_weapon_data(data))

    # Cross-reference validation
    validation_errors.extend(await validate_cross_references(data, data_type))

    # Compliance validation
    compliance_result = await srd_compliance_service.verify_data_compliance(
        data, data_type, "data_validation"
    )

    if not compliance_result.is_compliant:
        validation_errors.extend(compliance_result.issues)

    return validation_errors

async def validate_cross_references(data, data_type: str):
    """Validate cross-references in data."""
    errors = []

    if data_type == "spell":
        # Validate referenced monsters, items, etc.
        if hasattr(data, 'higher_levels') and data.higher_levels:
            # Validate higher level descriptions
            if "placeholder" in data.higher_levels.lower():
                errors.append("Spell contains placeholder text in higher levels")

    elif data_type == "monster":
        # Validate ability scores are within reasonable ranges
        ability_scores = [
            data.strength, data.dexterity, data.constitution,
            data.intelligence, data.wisdom, data.charisma
        ]

        for score in ability_scores:
            if score < 1 or score > 30:
                errors.append(f"Ability score {score} is outside valid range (1-30)")

    return errors
```

### 5. Backup and Recovery

```python
# Implement backup and recovery procedures
class SRDDataBackupManager:
    """Manage SRD data backups and recovery."""

    @staticmethod
    async def create_scheduled_backup(backup_type: str = "daily"):
        """Create scheduled backup."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"srd_{backup_type}_backup_{timestamp}"

        try:
            backup_path = await srd_database_manager.create_backup(backup_name)

            # Log backup creation
            srd_audit_service.log_system_operation(
                operation="backup_created",
                details={"backup_name": backup_name, "path": backup_path},
                user="system"
            )

            logger.info(f"SRD backup created: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            raise

    @staticmethod
    async def restore_from_backup(backup_path: str, user: str):
        """Restore from backup."""
        try:
            # Create pre-restore backup
            emergency_backup = await srd_database_manager.create_backup(
                "emergency_backup_before_restore"
            )

            # Perform restore
            await srd_database_manager.restore_from_backup(backup_path)

            # Log restore operation
            srd_audit_service.log_system_operation(
                operation="backup_restored",
                details={
                    "backup_path": backup_path,
                    "emergency_backup": emergency_backup
                },
                user=user
            )

            logger.info(f"SRD restored from backup: {backup_path}")

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Problems

```python
# Diagnose database connection issues
async def diagnose_database_connection():
    """Diagnose SRD database connection issues."""

    try:
        # Test basic connection
        stats = await srd_database_manager.get_database_stats()
        print(f"Database connection successful. Total monsters: {stats['monster_count']}")

        # Test specific operations
        test_monster = await srd_database_manager.get_monster_by_name("goblin")
        if test_monster:
            print("Monster lookup successful")
        else:
            print("Warning: Test monster lookup failed")

    except Exception as e:
        print(f"Database connection failed: {e}")

        # Check database file
        if not os.path.exists(srd_database_manager.database_path):
            print(f"Database file does not exist: {srd_database_manager.database_path}")

        # Check file permissions
        try:
            with open(srd_database_manager.database_path, 'rb') as f:
                f.read(1)
            print("Database file is readable")
        except Exception as perm_error:
            print(f"Database file permission issue: {perm_error}")
```

#### 2. Compliance Verification Issues

```python
# Troubleshoot compliance verification
async def troubleshoot_compliance_verification():
    """Troubleshoot SRD compliance verification issues."""

    try:
        # Test compliance service
        test_data = await srd_database_manager.get_monster_by_name("goblin")

        if not test_data:
            print("Cannot test compliance: no test data available")
            return

        compliance_result = await srd_compliance_service.verify_data_compliance(
            test_data, "monster", "troubleshooting"
        )

        print(f"Compliance check result: {compliance_result.is_compliant}")

        if not compliance_result.is_compliant:
            print("Compliance issues found:")
            for issue in compliance_result.issues:
                print(f"  - {issue}")

    except Exception as e:
        print(f"Compliance verification failed: {e}")

        # Check compliance database
        if not os.path.exists(srd_compliance_service.database_path):
            print(f"Compliance database does not exist: {srd_compliance_service.database_path}")
```

#### 3. Import/Export Problems

```python
# Troubleshoot data import/export
async def troubleshoot_data_import():
    """Troubleshoot SRD data import issues."""

    try:
        # Test import service
        test_data = {
            "monster_name": "Test Monster",
            "armor_class": 12,
            "hit_points": "10 (1d8 + 2)",
            "challenge_rating": 0.25
        }

        validation_result = await srd_data_import_service.validate_import_data(
            test_data, "monster"
        )

        if validation_result.is_valid:
            print("Import validation successful")
        else:
            print("Import validation failed:")
            for error in validation_result.errors:
                print(f"  - {error}")

    except Exception as e:
        print(f"Import troubleshooting failed: {e}")
```

#### 4. Performance Issues

```python
# Monitor and optimize SRD performance
async def monitor_srd_performance():
    """Monitor SRD service performance."""

    start_time = time.time()

    # Test various operations
    operations = [
        ("monster_lookup", lambda: srd_database_manager.get_monster_by_name("goblin")),
        ("spell_lookup", lambda: srd_database_manager.get_spells_by_level(0)),
        ("weapon_lookup", lambda: srd_database_manager.get_weapons_by_category("Simple Melee Weapons")),
        ("compliance_check", lambda: srd_compliance_service.verify_data_compliance(
            srd_database_manager.get_monster_by_name("goblin"), "monster", "performance_test"
        )),
    ]

    results = {}

    for operation_name, operation_func in operations:
        try:
            op_start = time.time()
            result = await operation_func()
            op_end = time.time()

            results[operation_name] = {
                "duration": op_end - op_start,
                "success": True,
                "result_count": len(result) if hasattr(result, '__len__') else 1
            }
        except Exception as e:
            results[operation_name] = {
                "duration": 0,
                "success": False,
                "error": str(e)
            }

    total_time = time.time() - start_time

    # Report results
    print(f"SRD Performance Test Results ({total_time:.2f}s total):")
    for operation_name, result in results.items():
        status = "✓" if result["success"] else "✗"
        print(f"  {status} {operation_name}: {result['duration']:.3f}s")

        if not result["success"]:
            print(f"      Error: {result['error']}")

    # Performance recommendations
    slow_operations = [
        name for name, result in results.items()
        if result["success"] and result["duration"] > 0.1
    ]

    if slow_operations:
        print(f"\nSlow operations detected: {', '.join(slow_operations)}")
        print("Consider implementing caching or optimizing database queries")
```

#### 5. Memory Usage Issues

```python
# Monitor and manage memory usage
class SRDMemoryManager:
    """Manage SRD service memory usage."""

    def __init__(self, max_cache_size: int = 1000):
        self.max_cache_size = max_cache_size
        self.cache = {}
        self.access_times = {}

    def get_cached_data(self, key: str):
        """Get data from cache."""
        if key in self.cache:
            self.access_times[key] = time.time()
            return self.cache[key]
        return None

    def set_cached_data(self, key: str, data):
        """Set data in cache with LRU eviction."""
        if len(self.cache) >= self.max_cache_size:
            # Remove least recently used item
            lru_key = min(self.access_times, key=self.access_times.get)
            del self.cache[lru_key]
            del self.access_times[lru_key]

        self.cache[key] = data
        self.access_times[key] = time.time()

    def clear_cache(self):
        """Clear all cached data."""
        self.cache.clear()
        self.access_times.clear()

    def get_cache_stats(self):
        """Get cache statistics."""
        return {
            "cache_size": len(self.cache),
            "max_cache_size": self.max_cache_size,
            "cache_utilization": len(self.cache) / self.max_cache_size * 100
        }
```

## Security Considerations

### Access Control

```python
# Implement access control for SRD data
class SRDAccessControl:
    """Control access to SRD data."""

    def __init__(self):
        self.access_rules = {
            "admin": {"read": True, "write": True, "delete": True},
            "dm": {"read": True, "write": True, "delete": False},
            "player": {"read": True, "write": False, "delete": False},
            "ai_agent": {"read": True, "write": False, "delete": False}
        }

    def check_access(self, user_role: str, operation: str) -> bool:
        """Check if user role has access to operation."""
        if user_role not in self.access_rules:
            return False

        return self.access_rules[user_role].get(operation, False)

    def audit_access_attempt(self, user: str, operation: str, data_type: str, success: bool):
        """Audit access attempts."""
        srd_audit_service.log_security_event(
            event_type="access_attempt",
            details={
                "user": user,
                "operation": operation,
                "data_type": data_type,
                "success": success
            }
        )
```

### Data Validation

```python
# Validate SRD data integrity
async def validate_srd_data_integrity():
    """Validate integrity of SRD data."""

    integrity_issues = []

    # Check database integrity
    try:
        stats = await srd_database_manager.get_database_stats()

        # Validate record counts are reasonable
        if stats["monster_count"] < 100:
            integrity_issues.append("Low monster count - possible data loss")

        if stats["spell_count"] < 300:
            integrity_issues.append("Low spell count - possible data loss")

        # Validate data consistency
        monsters = await srd_database_manager.get_monsters_by_challenge_rating(0, 30)
        for monster in monsters:
            if monster.armor_class < 5 or monster.armor_class > 25:
                integrity_issues.append(f"Invalid AC for {monster.monster_name}: {monster.armor_class}")

    except Exception as e:
        integrity_issues.append(f"Database integrity check failed: {e}")

    return integrity_issues
```

### Audit Trail Security

```python
# Secure audit trail management
async def secure_audit_logging(data, operation: str, user: str):
    """Securely log audit events."""

    # Create tamper-proof audit record
    audit_record = {
        "timestamp": datetime.utcnow().isoformat(),
        "user": user,
        "operation": operation,
        "data_type": type(data).__name__,
        "data_id": getattr(data, 'id', None),
        "data_hash": SRDDataVerificationService.generate_verification_hash(data)
    }

    # Add digital signature or HMAC for integrity
    import hmac
    import hashlib

    secret_key = os.getenv("SRD_AUDIT_SECRET_KEY")
    if secret_key:
        signature = hmac.new(
            secret_key.encode(),
            json.dumps(audit_record).encode(),
            hashlib.sha256
        ).hexdigest()
        audit_record["signature"] = signature

    # Log audit record
    await srd_audit_service.log_data_access(
        data=data,
        service="secure_audit",
        user=user,
        operation=operation,
        audit_metadata=audit_record
    )
```

This comprehensive guide covers all aspects of using the SRD Services effectively for managing D&D 5.1 System Reference Document data in the AI Dungeon Master system.