# AI Validation Service Usage Guide

## Overview

The AI Validation Service (`packages/backend/components/ai_validation_service.py`) provides comprehensive validation of AI-generated content against D&D 5.1 System Reference Document (SRD) rules to ensure accuracy, consistency, and compliance.

### Purpose
- Validate AI responses against official SRD rules
- Detect statistical inaccuracies in monster/npc data
- Ensure spell descriptions match SRD specifications
- Verify weapon properties and mechanics
- Track AI accuracy metrics and improvement feedback
- Provide corrections and suggestions for AI-generated content

## Key Components

### Classes

#### `AIValidationService`
Main service class for AI response validation.

**Key Methods:**
- `validate_ai_response(query, ai_response, expected_entities, validation_type)` - Main validation method
- `get_validation_metrics()` - Get accuracy metrics
- `generate_improvement_feedback(validation_result)` - Generate AI improvement suggestions
- `health_check()` - Service health status
- `reset_metrics()` - Reset validation metrics

#### `ValidationResult`
Dataclass containing validation results.

**Attributes:**
- `is_accurate`: Boolean indicating if response passes validation
- `accuracy_score`: Float score between 0.0 and 1.0
- `issues_found`: List of identified issues
- `corrections_suggested`: List of suggested corrections
- `validation_details`: Detailed validation information
- `validated_at`: Timestamp of validation
- `validation_type`: Type of validation performed

#### `ValidationMetrics`
Tracks validation accuracy and performance.

**Attributes:**
- `total_validations`: Total number of validations performed
- `accurate_responses`: Number of accurate responses
- `accuracy_rate`: Overall accuracy percentage
- `average_accuracy_score`: Average accuracy score
- `common_issues`: Dictionary of frequently occurring issues
- `validation_types`: Dictionary of validation type counts

### Validation Rules

The service includes validation for:
- **Stat Blocks**: Armor class, hit points, challenge rating validation
- **Damage Values**: Dice notation and damage calculations
- **Spell Descriptions**: Level, casting time, range, components
- **Monster Abilities**: Special abilities and traits
- **Weapon Properties**: Damage, properties, categories
- **Challenge Ratings**: CR calculations and XP values
- **Saving Throws**: Save DC and ability validation
- **Ability Scores**: Score ranges and modifiers

## Dependencies

### Internal Dependencies
- `packages.backend.components.rules_engine` - SRD data access
- `packages.shared.logging_config` - Structured logging

### External Dependencies
- `re` - Regular expressions for text parsing
- `datetime` - Timestamp handling

## Configuration

The service is initialized with default validation rules:

```python
# Default initialization
validation_service = AIValidationService()
```

### Terminology Rules
```python
# Common D&D terms and their corrections
terminology_rules = {
    "hit points": ["hp", "hit points", "health points"],
    "armor class": ["ac", "armor class"],
    "challenge rating": ["cr", "challenge rating"],
    "proficiency bonus": ["proficiency", "prof bonus", "proficiency bonus"],
    "saving throw": ["save", "saving throw"],
    "spell slot": ["spell slot", "spell slots"],
}
```

## Usage Examples

### Basic Response Validation

```python
from packages.backend.components.ai_validation_service import ai_validation_service

# Validate AI response
validation_result = await ai_validation_service.validate_ai_response(
    query="Tell me about a goblin",
    ai_response="A goblin has 7 hit points, 15 AC, and is CR 1/4.",
    expected_entities=["goblin"],
    validation_type="monster_info"
)

# Check results
if validation_result.is_accurate:
    print(f"Response is accurate with score: {validation_result.accuracy_score}")
else:
    print(f"Issues found: {validation_result.issues_found}")
    print(f"Suggested corrections: {validation_result.corrections_suggested}")
```

### Monster Stat Validation

```python
# Validate monster statistics
ai_response = """
The orc warrior has:
- Armor Class: 16 (chain mail)
- Hit Points: 18 (4d8 + 4)
- Challenge Rating: 1/2 (100 XP)
- Strength: 16 (+3)
"""

result = await ai_validation_service.validate_ai_response(
    query="What are the stats for an orc warrior?",
    ai_response=ai_response,
    expected_entities=["orc"],
    validation_type="monster_stats"
)

print(f"Accuracy Score: {result.accuracy_score}")
for issue in result.issues_found:
    print(f"Issue: {issue}")
```

### Spell Description Validation

```python
# Validate spell information
ai_response = """
Fireball is a 3rd level evocation spell that requires:
- Casting time: 1 action
- Range: 150 feet
- Duration: Instantaneous
- Components: V, S, M (bat guano and sulfur)
"""

result = await ai_validation_service.validate_ai_response(
    query="Describe the fireball spell",
    ai_response=ai_response,
    expected_entities=["fireball"],
    validation_type="spell_info"
)
```

### Weapon Properties Validation

```python
# Validate weapon information
ai_response = """
The longsword is a martial melee weapon that:
- Deals 1d8 slashing damage
- Has the versatile property (1d10 when used two-handed)
- Costs 15 gp and weighs 3 lbs
- Is available to fighters and paladins
"""

result = await ai_validation_service.validate_ai_response(
    query="Tell me about the longsword",
    ai_response=ai_response,
    expected_entities=["longsword"],
    validation_type="weapon_info"
)
```

## Error Handling

### Validation Failures
```python
from packages.backend.components.ai_validation_service import AIValidationService

try:
    result = await ai_validation_service.validate_ai_response(
        query="monster info",
        ai_response="response text",
        validation_type="general"
    )
except Exception as e:
    logger.error(f"Validation failed: {e}")
    # Continue with unvalidated response or use fallback
```

### Missing SRD Data
```python
# Handle cases where entities aren't in SRD
result = await ai_validation_service.validate_ai_response(
    query="Tell me about a custom monster",
    ai_response="Custom monster description",
    expected_entities=["custom_monster"],
    validation_type="custom_content"
)

# Check for "not found" issues
for issue in result.issues_found:
    if "not found in official SRD" in issue:
        logger.info("Custom content detected - no SRD validation available")
```

## Integration Points

### With AI Client
```python
# packages/backend/components/ai_client.py
from packages.backend.components.ai_validation_service import ai_validation_service

class AIClient:
    def __init__(self):
        self.validation_service = ai_validation_service

    async def generate_validated_text(self, prompt: str) -> dict:
        """Generate text and validate it."""
        # Generate response
        response = await self.generate_text(prompt)

        # Validate response
        validation = await self.validation_service.validate_ai_response(
            query=prompt,
            ai_response=response,
            validation_type="generated_content"
        )

        return {
            "response": response,
            "validation": validation,
            "is_accurate": validation.is_accurate,
            "accuracy_score": validation.accuracy_score
        }
```

### With Dungeon Master Agent
```python
# packages/backend/agents/dm_graph.py
from packages.backend.components.ai_validation_service import ai_validation_service

class DungeonMasterAgent:
    """AI Dungeon Master with validation."""

    def __init__(self):
        self.validation_service = ai_validation_service

    async def generate_monster_description(self, monster_name: str) -> dict:
        """Generate and validate monster description."""
        prompt = f"Describe the {monster_name} from D&D 5.1 SRD"

        # Generate description
        description = await self.ai_client.generate_text(prompt)

        # Validate against SRD
        validation = await self.validation_service.validate_ai_response(
            query=prompt,
            ai_response=description,
            expected_entities=[monster_name],
            validation_type="monster_description"
        )

        # Return with validation results
        return {
            "monster": monster_name,
            "description": description,
            "validation": validation,
            "needs_correction": not validation.is_accurate
        }

    async def generate_spell_description(self, spell_name: str) -> dict:
        """Generate and validate spell description."""
        prompt = f"Describe the {spell_name} spell from D&D 5.1 SRD"

        description = await self.ai_client.generate_text(prompt)

        validation = await self.validation_service.validate_ai_response(
            query=prompt,
            ai_response=description,
            expected_entities=[spell_name],
            validation_type="spell_description"
        )

        return {
            "spell": spell_name,
            "description": description,
            "validation": validation
        }
```

### With Rules Engine
```python
# Integration with rules engine for data access
from packages.backend.components.rules_engine import rules_engine
from packages.backend.components.ai_validation_service import ai_validation_service

async def validate_and_correct_monster(monster_name: str, ai_description: str) -> dict:
    """Validate AI monster description and provide corrections."""

    # Get official data from rules engine
    official_data = await rules_engine.query_monster(monster_name)

    if not official_data.found:
        return {"error": f"Monster {monster_name} not found in SRD"}

    # Validate AI description
    validation = await ai_validation_service.validate_ai_response(
        query=f"Describe {monster_name}",
        ai_response=ai_description,
        expected_entities=[monster_name],
        validation_type="monster_validation"
    )

    # Generate correction suggestions
    corrections = []
    if not validation.is_accurate:
        for issue in validation.issues_found:
            if "Armor Class" in issue:
                corrections.append(f"Use official AC: {official_data.data.armor_class}")
            elif "Hit Points" in issue:
                corrections.append(f"Use official HP: {official_data.data.hit_points}")
            elif "Challenge Rating" in issue:
                corrections.append(f"Use official CR: {official_data.data.challenge_rating}")

    return {
        "original_description": ai_description,
        "validation": validation,
        "official_data": official_data.data,
        "corrections": corrections,
        "improvement_feedback": ai_validation_service.generate_improvement_feedback(validation)
    }
```

### With Memory Service
```python
# packages/backend/components/memory_service.py
from packages.backend.components.ai_validation_service import ai_validation_service

class MemoryService:
    """Memory service with AI validation."""

    async def store_validated_memory(self, content: str, source: str) -> dict:
        """Store content only if it passes validation."""

        # Validate content before storing
        validation = await ai_validation_service.validate_ai_response(
            query=f"Validate content from {source}",
            ai_response=content,
            validation_type="memory_content"
        )

        # Store with validation metadata
        memory_entry = {
            "content": content,
            "source": source,
            "validation": {
                "is_accurate": validation.is_accurate,
                "accuracy_score": validation.accuracy_score,
                "issues": validation.issues_found,
                "validated_at": validation.validated_at
            },
            "quality_score": validation.accuracy_score
        }

        # Only store if accuracy is sufficient
        if validation.accuracy_score >= 0.7:
            await self.store_memory(memory_entry)
            return {"stored": True, "validation": validation}
        else:
            return {"stored": False, "validation": validation, "reason": "Low accuracy score"}
```

## Metrics and Monitoring

### Getting Validation Metrics
```python
# Get current validation statistics
metrics = ai_validation_service.get_validation_metrics()

print(f"Total Validations: {metrics['total_validations']}")
print(f"Accuracy Rate: {metrics['accuracy_rate']}")
print(f"Average Score: {metrics['average_accuracy_score']}")
print(f"Common Issues: {metrics['top_issues']}")
```

### Health Monitoring
```python
# Service health check
health = ai_validation_service.health_check()

if health["status"] == "healthy":
    print("AI Validation Service is operational")
    print(f"Validation rules loaded: {health['validation_rules_loaded']}")
else:
    print(f"Service unhealthy: {health['error']}")
```

### Performance Monitoring
```python
# Monitor validation performance
import time

start_time = time.time()
result = await ai_validation_service.validate_ai_response(
    query="test query",
    ai_response="test response",
    validation_type="performance_test"
)
validation_time = time.time() - start_time

print(f"Validation time: {validation_time:.3f} seconds")
print(f"Accuracy score: {result.accuracy_score}")
```

## Advanced Features

### Custom Validation Rules
```python
# Extend validation service with custom rules
class CustomAIValidationService(AIValidationService):
    def __init__(self):
        super().__init__()
        self.add_custom_validation_rules()

    def add_custom_validation_rules(self):
        """Add custom validation rules."""
        self.validation_rules["custom_content"] = self._validate_custom_content
        self.validation_rules["house_rules"] = self._validate_house_rules

    def _validate_custom_content(self, query: str, response: str) -> dict:
        """Custom validation logic."""
        issues = []
        corrections = []

        # Add your custom validation logic here
        if "custom_term" in response.lower():
            issues.append("Custom term detected - verify house rules compliance")

        return {"issues": issues, "corrections": corrections}
```

### Batch Validation
```python
# Validate multiple responses efficiently
async def batch_validate_responses(responses: List[dict]) -> List[ValidationResult]:
    """Validate multiple AI responses."""

    validation_tasks = []
    for response_data in responses:
        task = ai_validation_service.validate_ai_response(
            query=response_data["query"],
            ai_response=response_data["response"],
            expected_entities=response_data.get("entities", []),
            validation_type=response_data.get("type", "batch")
        )
        validation_tasks.append(task)

    # Run validations concurrently
    return await asyncio.gather(*validation_tasks)
```

### Validation Feedback Loop
```python
# Use validation results to improve AI prompts
async def improve_ai_response(original_query: str, ai_response: str) -> str:
    """Improve AI response based on validation feedback."""

    # Validate original response
    validation = await ai_validation_service.validate_ai_response(
        query=original_query,
        ai_response=ai_response,
        validation_type="improvement"
    )

    if validation.is_accurate:
        return ai_response  # No improvement needed

    # Generate improvement prompt
    improvement_prompt = f"""
    Original Query: {original_query}
    Original Response: {ai_response}

    Issues Found:
    {chr(10).join(f"- {issue}" for issue in validation.issues_found)}

    Suggested Corrections:
    {chr(10).join(f"- {correction}" for correction in validation.corrections_suggested)}

    Please provide an improved response that addresses these issues.
    """

    # Generate improved response
    improved_response = await ai_client.generate_text(improvement_prompt)

    return improved_response
```

## Best Practices

### 1. Validation Strategy
```python
# Always validate critical content
critical_types = ["monster_stats", "spell_mechanics", "rule_explanation"]

async def validate_critical_content(content: str, content_type: str) -> bool:
    """Validate critical game content."""
    if content_type in critical_types:
        validation = await ai_validation_service.validate_ai_response(
            query=f"Validate {content_type}",
            ai_response=content,
            validation_type=content_type
        )
        return validation.accuracy_score >= 0.9  # High threshold for critical content
    return True  # Don't block non-critical content
```

### 2. Error Handling
```python
# Graceful handling of validation failures
async def safe_validate(query: str, response: str) -> ValidationResult:
    """Safely validate with error handling."""
    try:
        return await ai_validation_service.validate_ai_response(
            query=query,
            ai_response=response,
            validation_type="safe_validation"
        )
    except Exception as e:
        logger.error(f"Validation error: {e}")
        # Return minimal validation result on error
        return ValidationResult(
            is_accurate=True,  # Assume accurate if validation fails
            accuracy_score=0.5,  # Neutral score
            issues_found=[f"Validation error: {e}"],
            corrections_suggested=["Manual review recommended"],
            validation_details=[],
            validated_at=datetime.utcnow(),
            validation_type="error_fallback"
        )
```

### 3. Performance Optimization
```python
# Cache validation results for similar content
from functools import lru_cache

@lru_cache(maxsize=1000)
async def cached_validate(query: str, response: str) -> ValidationResult:
    """Cache validation results for performance."""
    return await ai_validation_service.validate_ai_response(
        query=query,
        ai_response=response,
        validation_type="cached"
    )
```

### 4. Logging and Monitoring
```python
# Comprehensive logging for validation operations
async def validate_with_logging(query: str, response: str) -> ValidationResult:
    """Validate with detailed logging."""
    start_time = datetime.utcnow()

    logger.info("Starting AI response validation", query_length=len(query), response_length=len(response))

    result = await ai_validation_service.validate_ai_response(
        query=query,
        ai_response=response,
        validation_type="logged"
    )

    validation_time = datetime.utcnow() - start_time

    logger.info(
        "AI response validation completed",
        validation_time_ms=validation_time.total_seconds() * 1000,
        is_accurate=result.is_accurate,
        accuracy_score=result.accuracy_score,
        issues_count=len(result.issues_found)
    )

    return result
```

### 5. Configuration Management
```python
# Configure validation thresholds
class ValidationConfig:
    """Configuration for validation thresholds."""
    MIN_ACCURACY_THRESHOLD = 0.8
    CRITICAL_CONTENT_THRESHOLD = 0.95
    LOG_ISSUES_BELOW_THRESHOLD = 0.7

async def validate_with_config(query: str, response: str, content_type: str) -> ValidationResult:
    """Validate using configuration thresholds."""
    result = await ai_validation_service.validate_ai_response(
        query=query,
        ai_response=response,
        validation_type=content_type
    )

    # Log low accuracy responses
    if result.accuracy_score < ValidationConfig.LOG_ISSUES_BELOW_THRESHOLD:
        logger.warning(
            "Low accuracy validation result",
            accuracy_score=result.accuracy_score,
            content_type=content_type,
            issues=result.issues_found
        )

    # Critical content validation
    if content_type in ["rules", "mechanics"] and result.accuracy_score < ValidationConfig.CRITICAL_CONTENT_THRESHOLD:
        logger.error(
            "Critical content validation failed",
            accuracy_score=result.accuracy_score,
            content_type=content_type,
            issues=result.issues_found
        )

    return result
```

## Troubleshooting

### Common Issues

#### 1. Entity Not Found
```python
# Handle missing SRD entities
result = await ai_validation_service.validate_ai_response(
    query="Tell me about a custom monster",
    ai_response="Custom monster stats",
    expected_entities=["custom_monster"],
    validation_type="custom"
)

# Check for "not found" issues
for issue in result.issues_found:
    if "not found in official SRD" in issue:
        print("Custom entity - no SRD validation available")
        # Handle custom content appropriately
```

#### 2. Validation Timeouts
```python
# Handle validation timeouts
import asyncio

async def validate_with_timeout(query: str, response: str, timeout: float = 10.0) -> ValidationResult:
    """Validate with timeout protection."""
    try:
        return await asyncio.wait_for(
            ai_validation_service.validate_ai_response(
                query=query,
                ai_response=response,
                validation_type="timeout_protected"
            ),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.warning("Validation timeout - using fallback")
        return ValidationResult(
            is_accurate=True,
            accuracy_score=0.5,
            issues_found=["Validation timeout"],
            corrections_suggested=["Manual review recommended"],
            validation_details=[],
            validated_at=datetime.utcnow(),
            validation_type="timeout_fallback"
        )
```

#### 3. Memory Issues
```python
# Handle memory constraints with streaming validation
async def validate_large_content(query: str, large_response: str, chunk_size: int = 1000) -> ValidationResult:
    """Validate large content in chunks."""
    chunks = [large_response[i:i + chunk_size] for i in range(0, len(large_response), chunk_size)]

    all_issues = []
    total_score = 0.0

    for i, chunk in enumerate(chunks):
        chunk_query = f"{query} (chunk {i + 1}/{len(chunks)})"
        chunk_result = await ai_validation_service.validate_ai_response(
            query=chunk_query,
            ai_response=chunk,
            validation_type="chunked"
        )

        all_issues.extend(chunk_result.issues_found)
        total_score += chunk_result.accuracy_score

    # Aggregate results
    average_score = total_score / len(chunks)

    return ValidationResult(
        is_accurate=average_score >= 0.8,
        accuracy_score=average_score,
        issues_found=all_issues,
        corrections_suggested=list(set(all_issues)),  # Remove duplicates
        validation_details=[f"Validated {len(chunks)} chunks"],
        validated_at=datetime.utcnow(),
        validation_type="chunked_validation"
    )
```

#### 4. Rules Engine Integration Issues
```python
# Handle rules engine connectivity issues
async def validate_with_fallback(query: str, response: str) -> ValidationResult:
    """Validate with rules engine fallback."""
    try:
        return await ai_validation_service.validate_ai_response(
            query=query,
            ai_response=response,
            validation_type="standard"
        )
    except Exception as e:
        if "rules engine" in str(e).lower():
            logger.warning("Rules engine unavailable - using basic validation")

            # Fallback to basic terminology validation
            issues = ai_validation_service._validate_terminology(response)

            return ValidationResult(
                is_accurate=len(issues) == 0,
                accuracy_score=max(0.0, 1.0 - (len(issues) * 0.1)),
                issues_found=issues,
                corrections_suggested=issues,  # Same as issues for terminology
                validation_details=["Basic terminology validation only"],
                validated_at=datetime.utcnow(),
                validation_type="fallback_validation"
            )
        else:
            raise
```

## Security Considerations

### Input Sanitization
```python
# Sanitize inputs before validation
import re

def sanitize_validation_input(text: str) -> str:
    """Sanitize text for validation processing."""
    # Remove potentially problematic characters
    sanitized = re.sub(r'[^\w\s\.,!?-]', '', text)
    # Limit length to prevent memory issues
    return sanitized[:10000]  # 10k character limit
```

### Output Validation
```python
# Validate validation results for consistency
def validate_validation_result(result: ValidationResult) -> bool:
    """Validate that validation results are consistent."""
    if result.accuracy_score < 0.0 or result.accuracy_score > 1.0:
        logger.error(f"Invalid accuracy score: {result.accuracy_score}")
        return False

    if result.is_accurate and result.accuracy_score < 0.8:
        logger.warning("Inconsistent accuracy: marked accurate but low score")
        return False

    return True
```

### Rate Limiting
```python
# Implement rate limiting for validation requests
from datetime import datetime, timedelta

class ValidationRateLimiter:
    """Rate limiter for validation requests."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = []

    def is_allowed(self) -> bool:
        """Check if request is allowed."""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=self.window_seconds)

        # Remove old requests
        self.requests = [req for req in self.requests if req > window_start]

        if len(self.requests) >= self.max_requests:
            return False

        self.requests.append(now)
        return True

# Use rate limiter
rate_limiter = ValidationRateLimiter()

async def rate_limited_validate(query: str, response: str) -> ValidationResult:
    """Validate with rate limiting."""
    if not rate_limiter.is_allowed():
        raise Exception("Validation rate limit exceeded")

    return await ai_validation_service.validate_ai_response(
        query=query,
        ai_response=response,
        validation_type="rate_limited"
    )
```

This comprehensive guide covers all aspects of using the AI Validation Service effectively for ensuring AI-generated D&D content accuracy and compliance.