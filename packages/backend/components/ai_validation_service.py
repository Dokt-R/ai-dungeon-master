"""
AI Validation Service for D&D 5.1 System Reference Document.

This module provides AI response validation against SRD rules to ensure accuracy
and compliance in AI-generated D&D content.

Features:
- AI response accuracy validation against SRD rules
- Validation metrics and accuracy tracking
- Feedback generation for AI improvement
- Integration with system prompt enhancement
- Comprehensive validation reporting
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from packages.backend.components.rules_engine import rules_engine
from packages.shared.logging_config import get_logger


@dataclass
class ValidationResult:
    """Result of AI response validation."""

    is_accurate: bool
    accuracy_score: float
    issues_found: List[str]
    corrections_suggested: List[str]
    validation_details: List[str]
    validated_at: datetime
    validation_type: str


@dataclass
class ValidationMetrics:
    """Metrics for AI response validation."""

    total_validations: int = 0
    accurate_responses: int = 0
    accuracy_rate: float = 0.0
    average_accuracy_score: float = 0.0
    common_issues: Dict[str, int] = None
    validation_types: Dict[str, int] = None

    def __post_init__(self):
        if self.common_issues is None:
            self.common_issues = {}
        if self.validation_types is None:
            self.validation_types = {}


class AIValidationService:
    """
    Service for validating AI responses against SRD rules.

    This service ensures AI-generated D&D content is accurate and compliant
    with official D&D 5.1 System Reference Document rules.
    """

    def __init__(self):
        self.logger = get_logger(f"{__name__}.AIValidationService")
        self.metrics = ValidationMetrics()

        # Validation rules and patterns
        self._init_validation_rules()

        self.logger.info("AI Validation Service initialized")

    def _init_validation_rules(self) -> None:
        """Initialize validation rules and patterns."""
        self.validation_rules = {
            "stat_blocks": self._validate_stat_blocks,
            "damage_values": self._validate_damage_values,
            "spell_descriptions": self._validate_spell_descriptions,
            "monster_abilities": self._validate_monster_abilities,
            "weapon_properties": self._validate_weapon_properties,
            "challenge_ratings": self._validate_challenge_ratings,
            "saving_throws": self._validate_saving_throws,
            "ability_scores": self._validate_ability_scores,
        }

        # Initialize validation methods
        self._init_validation_methods()

    def _init_validation_methods(self) -> None:
        """Initialize validation method references."""
        # This method ensures all validation methods are properly initialized
        pass

    def _validate_stat_blocks(self, response: str) -> List[str]:
        """Validate stat block information in AI response."""
        issues = []

        # Extract stat block patterns from the response
        stat_block_patterns = [
            r"Armor Class:?\s*(\d+)",
            r"Hit Points:?\s*([\d\w\s\(\)\+\-]+)",
            r"Speed:?\s*([^.\n]+)",
            r"STR\s+(\d+)\s*\(\+\d+\)",
            r"DEX\s+(\d+)\s*\(\+\d+\)",
            r"CON\s+(\d+)\s*\(\+\d+\)",
            r"INT\s+(\d+)\s*\(\+\d+\)",
            r"WIS\s+(\d+)\s*\(\+\d+\)",
            r"CHA\s+(\d+)\s*\(\+\d+\)",
        ]

        response_lower = response.lower()
        for pattern in stat_block_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                # Validate that ability scores are within reasonable D&D ranges (1-30)
                if "str" in pattern.lower() or "dex" in pattern.lower() or "con" in pattern.lower() or \
                   "int" in pattern.lower() or "wis" in pattern.lower() or "cha" in pattern.lower():
                    for match in matches:
                        if isinstance(match, str):
                            # Extract the number from the match
                            score_match = re.search(r"(\d+)", match)
                            if score_match:
                                score = int(score_match.group(1))
                                if score < 1 or score > 30:
                                    issues.append(f"Invalid ability score: {match} (must be 1-30)")

                # Validate armor class is reasonable
                if "armor class" in pattern.lower():
                    for match in matches:
                        if isinstance(match, str):
                            ac_match = re.search(r"(\d+)", match)
                            if ac_match:
                                ac = int(ac_match.group(1))
                                if ac < 5 or ac > 25:
                                    issues.append(f"Unusual Armor Class: {ac} (typically 5-25 for most creatures)")

        return issues

    def _validate_damage_values(self, response: str) -> List[str]:
        """Validate damage values and dice expressions."""
        issues = []

        # Find dice expressions like "1d8", "2d6 + 3", etc.
        dice_pattern = r"(\d+)d(\d+)(?:\s*[\+\-]\s*(\d+))?"
        dice_matches = re.findall(dice_pattern, response)

        for match in dice_matches:
            dice_count, dice_size, modifier = match
            dice_count = int(dice_count)
            dice_size = int(dice_size)

            # Check for valid dice sizes in D&D
            valid_sizes = [2, 3, 4, 6, 8, 10, 12, 20, 100]
            if dice_size not in valid_sizes:
                issues.append(f"Invalid dice size: {dice_size} (valid sizes: {valid_sizes})")

            # Check for reasonable dice counts
            if dice_count < 1 or dice_count > 20:
                issues.append(f"Unusual dice count: {dice_count} (typically 1-20)")

        return issues

    def _validate_spell_descriptions(self, response: str) -> List[str]:
        """Validate spell descriptions and mechanics."""
        issues = []

        response_lower = response.lower()

        # Check for common spell-related errors
        if "level 0" in response_lower:
            issues.append("Use 'cantrip' instead of 'level 0' for 0-level spells")

        # Check for proper spell component notation
        if "v,s,m" in response_lower and "verbal, somatic, material" not in response_lower:
            issues.append("Spell components should be written as 'V, S, M' not 'v,s,m'")

        return issues

    def _validate_monster_abilities(self, response: str) -> List[str]:
        """Validate monster abilities and traits."""
        issues = []

        response_lower = response.lower()

        # Check for common monster ability errors
        if "multiattack" in response_lower and "makes" not in response_lower:
            issues.append("Multiattack should specify how many attacks the creature makes")

        return issues

    def _validate_weapon_properties(self, response: str) -> List[str]:
        """Validate weapon properties and characteristics."""
        issues = []

        response_lower = response.lower()

        # Check for common weapon property errors
        if "versatile" in response_lower and "(1d8)" not in response_lower and "(1d10)" not in response_lower:
            issues.append("Versatile weapons should specify two-handed damage in parentheses")

        return issues

    def _validate_challenge_ratings(self, response: str) -> List[str]:
        """Validate challenge rating information."""
        issues = []

        # Look for CR mentions
        cr_pattern = r"challenge rating (\d+(?:/\d+)?)"
        cr_matches = re.findall(cr_pattern, response, re.IGNORECASE)

        for cr in cr_matches:
            try:
                if "/" in cr:
                    # Fractional CR like "1/8"
                    num, den = cr.split("/")
                    value = float(num) / float(den)
                else:
                    value = float(cr)

                if value < 0 or value > 30:
                    issues.append(f"Unusual Challenge Rating: {cr} (typically 0-30)")
            except ValueError:
                issues.append(f"Invalid Challenge Rating format: {cr}")

        return issues

    def _validate_saving_throws(self, response: str) -> List[str]:
        """Validate saving throw information."""
        issues = []

        response_lower = response.lower()

        # Check for proper saving throw format
        save_pattern = r"saving throws ([^\.\n]+)"
        save_matches = re.findall(save_pattern, response_lower)

        for saves in save_matches:
            # Should contain ability abbreviations like STR, DEX, etc.
            ability_abbrs = ["str", "dex", "con", "int", "wis", "cha"]
            found_abilities = [abbr for abbr in ability_abbrs if abbr in saves]

            if not found_abilities:
                issues.append("Saving throws should specify which abilities (STR, DEX, CON, INT, WIS, CHA)")

        return issues

    def _validate_ability_scores(self, response: str) -> List[str]:
        """Validate ability score information."""
        issues = []

        # Look for ability score patterns
        ability_pattern = r"(STR|DEX|CON|INT|WIS|CHA)\s+(\d+)\s*\(\+?[\-\+]?\d+\)"
        ability_matches = re.findall(ability_pattern, response, re.IGNORECASE)

        for ability, score in ability_matches:
            score = int(score)
            if score < 1 or score > 30:
                issues.append(f"Invalid {ability.upper()} score: {score} (must be 1-30)")

        return issues

        # Common D&D terms and their correct forms
        self.terminology_rules = {
            "hit points": ["hp", "hit points", "health points"],
            "armor class": ["ac", "armor class"],
            "challenge rating": ["cr", "challenge rating"],
            "proficiency bonus": ["proficiency", "prof bonus", "proficiency bonus"],
            "saving throw": ["save", "saving throw"],
            "spell slot": ["spell slot", "spell slots"],
            "concentration": ["concentration", "concentrating"],
            "advantage": ["advantage", "advantage on"],
            "disadvantage": ["disadvantage", "disadvantage on"],
        }

    async def validate_ai_response(
        self,
        query: str,
        ai_response: str,
        expected_entities: Optional[List[str]] = None,
        validation_type: str = "general",
    ) -> ValidationResult:
        """Validate AI response against SRD rules."""
        start_time = datetime.utcnow()

        try:
            issues = []
            corrections = []
            validation_details = []

            # Extract entities mentioned in the response
            mentioned_entities = self._extract_mentioned_entities(ai_response)

            # If specific entities were expected, check if they were mentioned
            if expected_entities:
                missing_entities = set(expected_entities) - set(mentioned_entities)
                if missing_entities:
                    issues.append(
                        f"Missing expected entities: {', '.join(missing_entities)}"
                    )
                    corrections.append(
                        f"Include information about: {', '.join(missing_entities)}"
                    )

            # Validate each mentioned entity
            entity_validations = []
            for entity in mentioned_entities:
                entity_validation = await self._validate_entity_mention(
                    entity, ai_response
                )
                entity_validations.append(entity_validation)

                if not entity_validation["is_accurate"]:
                    issues.extend(entity_validation["issues"])
                    corrections.extend(entity_validation["corrections"])

            # Perform content-specific validations
            content_validation = await self._validate_response_content(
                query, ai_response
            )
            issues.extend(content_validation.get("issues", []))
            corrections.extend(content_validation.get("corrections", []))

            # Calculate accuracy score
            accuracy_score = self._calculate_accuracy_score(issues, corrections)

            # Determine if response is accurate enough
            is_accurate = accuracy_score >= 0.8  # 80% accuracy threshold

            # Update metrics
            self._update_metrics(validation_type, is_accurate, accuracy_score, issues)

            result = ValidationResult(
                is_accurate=is_accurate,
                accuracy_score=accuracy_score,
                issues_found=issues,
                corrections_suggested=corrections,
                validation_details=validation_details,
                validated_at=datetime.utcnow(),
                validation_type=validation_type,
            )

            # Log validation result
            self.logger.info(
                "AI response validation completed",
                validation_type=validation_type,
                is_accurate=is_accurate,
                accuracy_score=".2f",
                issues_count=len(issues),
            )

            return result

        except Exception as e:
            self.logger.error("AI response validation failed", error=str(e))
            return ValidationResult(
                is_accurate=False,
                accuracy_score=0.0,
                issues_found=[f"Validation failed: {str(e)}"],
                corrections_suggested=["Manual review required"],
                validation_details=[],
                validated_at=datetime.utcnow(),
                validation_type=validation_type,
            )

    async def _validate_entity_mention(
        self, entity_name: str, ai_response: str
    ) -> Dict[str, Any]:
        """Validate a specific entity mentioned in the AI response."""
        validation_result = {
            "entity": entity_name,
            "is_accurate": True,
            "issues": [],
            "corrections": [],
        }

        try:
            # Try to find the entity in our SRD database
            # First, try as monster
            monster_result = await rules_engine.query_monster(entity_name)
            if monster_result.found:
                monster_issues = self._validate_monster_reference(
                    entity_name, ai_response, monster_result.data
                )
                validation_result["issues"].extend(monster_issues)
                return validation_result

            # Then try as spell
            spell_result = await rules_engine.query_spell(entity_name)
            if spell_result.found:
                spell_issues = self._validate_spell_reference(
                    entity_name, ai_response, spell_result.data
                )
                validation_result["issues"].extend(spell_issues)
                return validation_result

            # Then try as weapon
            weapon_result = await rules_engine.query_weapon(entity_name)
            if weapon_result.found:
                weapon_issues = self._validate_weapon_reference(
                    entity_name, ai_response, weapon_result.data
                )
                validation_result["issues"].extend(weapon_issues)
                return validation_result

            # Entity not found in SRD
            validation_result["is_accurate"] = False
            validation_result["issues"].append(
                f"Entity '{entity_name}' not found in official SRD"
            )

        except Exception as e:
            validation_result["is_accurate"] = False
            validation_result["issues"].append(f"Entity validation failed: {str(e)}")

        return validation_result

    def _validate_monster_reference(
        self, monster_name: str, ai_response: str, srd_data: Dict[str, Any]
    ) -> List[str]:
        """Validate AI response references to a specific monster."""
        issues = []

        # Extract monster stats from AI response
        ai_stats = self._extract_monster_stats_from_text(ai_response)

        # Compare with SRD data
        if (
            "armor_class" in ai_stats
            and abs(ai_stats["armor_class"] - srd_data.get("armor_class", 0)) > 2
        ):
            issues.append(
                f"Armor Class mismatch for {monster_name}: AI said {ai_stats['armor_class']}, SRD says {srd_data.get('armor_class')}"
            )

        if "hit_points" in ai_stats:
            # This is a rough comparison since HP can vary
            ai_hp = ai_stats["hit_points"]
            srd_hp = srd_data.get("hit_points", "")
            if not self._compare_hit_points(ai_hp, srd_hp):
                issues.append(f"Hit Points format incorrect for {monster_name}")

        if "challenge_rating" in ai_stats:
            ai_cr = ai_stats["challenge_rating"]
            srd_cr = srd_data.get("challenge_rating", "")
            if not self._compare_challenge_ratings(ai_cr, srd_cr):
                issues.append(
                    f"Challenge Rating mismatch for {monster_name}: AI said {ai_cr}, SRD says {srd_cr}"
                )

        return issues

    def _validate_spell_reference(
        self, spell_name: str, ai_response: str, srd_data: Dict[str, Any]
    ) -> List[str]:
        """Validate AI response references to a specific spell."""
        issues = []

        # Extract spell information from AI response
        ai_spell_info = self._extract_spell_info_from_text(ai_response)

        # Compare with SRD data
        if "level" in ai_spell_info and ai_spell_info["level"] != srd_data.get("level"):
            issues.append(
                f"Spell level mismatch for {spell_name}: AI said {ai_spell_info['level']}, SRD says {srd_data.get('level')}"
            )

        if "casting_time" in ai_spell_info:
            ai_casting_time = ai_spell_info["casting_time"].lower()
            srd_casting_time = srd_data.get("casting_time", "").lower()
            if not self._compare_casting_times(ai_casting_time, srd_casting_time):
                issues.append(f"Casting time mismatch for {spell_name}")

        if "range" in ai_spell_info:
            ai_range = ai_spell_info["range"].lower()
            srd_range = srd_data.get("range", "").lower()
            if not self._compare_ranges(ai_range, srd_range):
                issues.append(f"Range mismatch for {spell_name}")

        return issues

    def _validate_weapon_reference(
        self, weapon_name: str, ai_response: str, srd_data: Dict[str, Any]
    ) -> List[str]:
        """Validate AI response references to a specific weapon."""
        issues = []

        # Extract weapon information from AI response
        ai_weapon_info = self._extract_weapon_info_from_text(ai_response)

        # Compare with SRD data
        if "damage" in ai_weapon_info:
            ai_damage = ai_weapon_info["damage"].lower()
            srd_damage = srd_data.get("damage", "").lower()
            if not self._compare_damage(ai_damage, srd_damage):
                issues.append(
                    f"Damage mismatch for {weapon_name}: AI said {ai_damage}, SRD says {srd_damage}"
                )

        if "properties" in ai_weapon_info:
            ai_properties = set(p.lower() for p in ai_weapon_info["properties"])
            srd_properties = set(p.lower() for p in srd_data.get("properties", []))
            missing_properties = srd_properties - ai_properties
            if missing_properties:
                issues.append(
                    f"Missing properties for {weapon_name}: {', '.join(missing_properties)}"
                )

        return issues

    async def _validate_response_content(
        self, query: str, ai_response: str
    ) -> Dict[str, Any]:
        """Validate the overall content of the AI response."""
        issues = []
        corrections = []

        # Check for common D&D terminology errors
        terminology_issues = self._validate_terminology(ai_response)
        issues.extend(terminology_issues)

        # Check for factual inconsistencies
        factual_issues = await self._validate_factual_consistency(query, ai_response)
        issues.extend(factual_issues["issues"])
        corrections.extend(factual_issues["corrections"])

        # Check for rule violations
        rule_issues = self._validate_rule_compliance(ai_response)
        issues.extend(rule_issues["issues"])
        corrections.extend(rule_issues["corrections"])

        return {"issues": issues, "corrections": corrections}

    def _validate_terminology(self, text: str) -> List[str]:
        """Validate D&D terminology usage."""
        issues = []
        text_lower = text.lower()

        # Check for common misspellings or incorrect terms
        incorrect_terms = {
            "health points": "hit points",
            "health": "hit points (in combat context)",
            "mana": "spell slots",
            "magic points": "spell slots",
            "stamina": "hit points (in some contexts)",
            "defense": "armor class",
            "defence": "armor class",
        }

        for incorrect, correct in incorrect_terms.items():
            if incorrect in text_lower:
                issues.append(f"Terminology: '{incorrect}' should be '{correct}'")

        return issues

    async def _validate_factual_consistency(
        self, query: str, response: str
    ) -> Dict[str, List[str]]:
        """Validate factual consistency of the response."""
        issues = []
        corrections = []

        # Extract numerical values and check for consistency
        numbers = re.findall(r"\b(\d+)d(\d+)(?:\s*\+\s*(\d+))?", response)
        for match in numbers:
            dice_count, dice_size, modifier = match
            dice_count = int(dice_count)
            dice_size = int(dice_size)
            modifier = int(modifier) if modifier else 0

            # Check for obviously wrong dice (e.g., 1d2, 3d100)
            if dice_size not in [2, 3, 4, 6, 8, 10, 12, 20, 100]:
                issues.append(f"Unusual dice size: {dice_count}d{dice_size}")
                corrections.append(f"Verify dice size {dice_size} is correct for D&D")

        return {"issues": issues, "corrections": corrections}

    def _validate_rule_compliance(self, response: str) -> Dict[str, List[str]]:
        """Validate compliance with D&D rules."""
        issues = []
        corrections = []

        response_lower = response.lower()

        # Check for common rule misunderstandings
        if "critical hit on 19-20" in response_lower:
            issues.append("Critical hit range is incorrect")
            corrections.append("Critical hits occur on natural 20 only")

        if (
            "double damage on critical" in response_lower
            and "with magic weapon" not in response_lower
        ):
            issues.append("Critical hit damage rule may be incomplete")
            corrections.append(
                "Critical hits double dice damage, not including modifiers unless specified"
            )

        if "advantage and disadvantage cancel" in response_lower:
            issues.append("Advantage/Disadvantage rule oversimplified")
            corrections.append(
                "Multiple advantage/disadvantage sources require careful tracking"
            )

        return {"issues": issues, "corrections": corrections}

    def _extract_mentioned_entities(self, text: str) -> List[str]:
        """Extract D&D entity names mentioned in text."""
        entities = []

        # Common monster names
        monster_names = [
            "goblin",
            "orc",
            "dragon",
            "beholder",
            "mind flayer",
            "lich",
            "vampire",
            "werewolf",
            "zombie",
            "skeleton",
            "ghoul",
            "ghost",
            "wraith",
            "banshee",
            "basilisk",
            "chimera",
            "griffon",
            "hippogriff",
            "manticore",
            "owlbear",
            "displacer beast",
            "gelatinous cube",
            "black pudding",
            "ochre jelly",
        ]

        # Common spell names
        spell_names = [
            "fire bolt",
            "magic missile",
            "cure wounds",
            "shield",
            "invisibility",
            "detect magic",
            "light",
            "guidance",
            "resistance",
            "spare the dying",
            "eldritch blast",
            "chill touch",
            "poison spray",
            "shocking grasp",
            "fireball",
            "lightning bolt",
            "cone of cold",
            "wall of fire",
        ]

        # Common weapon names
        weapon_names = [
            "longsword",
            "shortsword",
            "dagger",
            "rapier",
            "greatsword",
            "bastard sword",
            "battleaxe",
            "handaxe",
            "greataxe",
            "warhammer",
            "maul",
            "mace",
            "club",
            "quarterstaff",
            "spear",
            "halberd",
            "glaive",
            "pike",
            "lance",
            "trident",
            "bow",
            "crossbow",
            "shortbow",
            "longbow",
            "hand crossbow",
            "heavy crossbow",
        ]

        text_lower = text.lower()

        # Find mentioned entities
        for entity_list, entity_type in [
            (monster_names, "monster"),
            (spell_names, "spell"),
            (weapon_names, "weapon"),
        ]:
            for entity in entity_list:
                if entity in text_lower:
                    # Avoid duplicates
                    if entity not in entities:
                        entities.append(entity)

        return entities

    def _extract_monster_stats_from_text(self, text: str) -> Dict[str, Any]:
        """Extract monster statistics from AI response text."""
        stats = {}

        # Extract armor class
        ac_match = re.search(r"armor class (\d+)", text.lower())
        if ac_match:
            stats["armor_class"] = int(ac_match.group(1))

        # Extract hit points
        hp_match = re.search(r"hit points (\d+)", text.lower())
        if hp_match:
            stats["hit_points"] = hp_match.group(1)

        # Extract challenge rating
        cr_match = re.search(r"challenge rating (\d+(?:/\d+)?)", text.lower())
        if cr_match:
            stats["challenge_rating"] = cr_match.group(1)

        return stats

    def _extract_spell_info_from_text(self, text: str) -> Dict[str, Any]:
        """Extract spell information from AI response text."""
        info = {}

        # Extract level
        level_match = re.search(r"(\d+)(?:st|nd|rd|th) level spell", text.lower())
        if level_match:
            info["level"] = int(level_match.group(1))
        elif "cantrip" in text.lower():
            info["level"] = 0

        # Extract casting time
        casting_time_match = re.search(r"casting time:?\s*([^.\n]+)", text.lower())
        if casting_time_match:
            info["casting_time"] = casting_time_match.group(1).strip()

        # Extract range
        range_match = re.search(r"range:?\s*([^.\n]+)", text.lower())
        if range_match:
            info["range"] = range_match.group(1).strip()

        return info

    def _extract_weapon_info_from_text(self, text: str) -> Dict[str, Any]:
        """Extract weapon information from AI response text."""
        info = {}

        # Extract damage
        damage_match = re.search(r"damage:?\s*([^.\n]+)", text.lower())
        if damage_match:
            info["damage"] = damage_match.group(1).strip()

        # Extract properties (this is more complex, simplified version)
        properties_match = re.search(r"properties:?\s*([^.\n]+)", text.lower())
        if properties_match:
            properties_text = properties_match.group(1)
            # Simple property extraction (could be improved)
            info["properties"] = [prop.strip() for prop in properties_text.split(",")]

        return info

    def _compare_hit_points(self, ai_hp: str, srd_hp: str) -> bool:
        """Compare hit point formats between AI and SRD."""
        # This is a simplified comparison - in practice, this would be more sophisticated
        ai_clean = re.sub(r"[^\d]", "", ai_hp)
        srd_clean = re.sub(r"[^\d]", "", srd_hp)

        if ai_clean and srd_clean:
            return abs(int(ai_clean) - int(srd_clean)) <= 5  # Allow small variance

        return True  # Can't compare, assume OK

    def _compare_challenge_ratings(self, ai_cr: str, srd_cr: str) -> bool:
        """Compare challenge rating formats."""
        # Normalize fractional CRs
        ai_normalized = ai_cr.replace("/", ".")
        srd_normalized = srd_cr.replace("/", ".")

        try:
            ai_value = float(ai_normalized)
            srd_value = float(srd_normalized)
            return abs(ai_value - srd_value) < 0.1  # Allow small variance
        except ValueError:
            return ai_normalized == srd_normalized

    def _compare_casting_times(self, ai_time: str, srd_time: str) -> bool:
        """Compare casting time formats."""
        # Normalize common variations
        ai_normalized = (
            ai_time.lower()
            .replace("action", "1 action")
            .replace("bonus action", "1 bonus action")
        )
        srd_normalized = (
            srd_time.lower()
            .replace("action", "1 action")
            .replace("bonus action", "1 bonus action")
        )

        return ai_normalized in srd_normalized or srd_normalized in ai_normalized

    def _compare_ranges(self, ai_range: str, srd_range: str) -> bool:
        """Compare range formats."""
        ai_normalized = ai_range.lower().replace("feet", "ft").replace("self", "self ")
        srd_normalized = (
            srd_range.lower().replace("feet", "ft").replace("self", "self ")
        )

        return ai_normalized in srd_normalized or srd_normalized in ai_normalized

    def _compare_damage(self, ai_damage: str, srd_damage: str) -> bool:
        """Compare damage formats."""
        # Remove common variations in formatting
        ai_normalized = ai_damage.lower().replace(" ", "").replace("damage", "")
        srd_normalized = srd_damage.lower().replace(" ", "").replace("damage", "")

        return ai_normalized in srd_normalized or srd_normalized in ai_normalized

    def _calculate_accuracy_score(
        self, issues: List[str], corrections: List[str]
    ) -> float:
        """Calculate accuracy score based on issues and corrections."""
        if not issues and not corrections:
            return 1.0  # Perfect score

        # Base score
        score = 0.8

        # Deduct for each issue
        score -= len(issues) * 0.1

        # Deduct for corrections needed
        score -= len(corrections) * 0.05

        # Ensure score stays in valid range
        return max(0.0, min(1.0, score))

    def _update_metrics(
        self,
        validation_type: str,
        is_accurate: bool,
        accuracy_score: float,
        issues: List[str],
    ) -> None:
        """Update validation metrics."""
        self.metrics.total_validations += 1
        if is_accurate:
            self.metrics.accurate_responses += 1

        # Update accuracy rate
        self.metrics.accuracy_rate = (
            self.metrics.accurate_responses / self.metrics.total_validations
        )

        # Update average accuracy score
        total_score = self.metrics.average_accuracy_score * (
            self.metrics.total_validations - 1
        )
        self.metrics.average_accuracy_score = (
            total_score + accuracy_score
        ) / self.metrics.total_validations

        # Update validation type counts
        if validation_type not in self.metrics.validation_types:
            self.metrics.validation_types[validation_type] = 0
        self.metrics.validation_types[validation_type] += 1

        # Update common issues
        for issue in issues:
            if issue not in self.metrics.common_issues:
                self.metrics.common_issues[issue] = 0
            self.metrics.common_issues[issue] += 1

    def get_validation_metrics(self) -> Dict[str, Any]:
        """Get current validation metrics."""
        return {
            "total_validations": self.metrics.total_validations,
            "accurate_responses": self.metrics.accurate_responses,
            "accuracy_rate": round(self.metrics.accuracy_rate, 3),
            "average_accuracy_score": round(self.metrics.average_accuracy_score, 3),
            "validation_types": dict(self.metrics.validation_types),
            "top_issues": sorted(
                self.metrics.common_issues.items(), key=lambda x: x[1], reverse=True
            )[:10],
        }

    def generate_improvement_feedback(
        self, validation_result: ValidationResult
    ) -> Dict[str, Any]:
        """Generate feedback for AI improvement based on validation results."""
        feedback = {
            "overall_accuracy": validation_result.accuracy_score,
            "strengths": [],
            "improvement_areas": [],
            "specific_corrections": validation_result.corrections_suggested,
            "pattern_analysis": [],
        }

        # Analyze patterns in issues
        issue_categories = self._categorize_issues(validation_result.issues_found)

        if not validation_result.issues_found:
            feedback["strengths"].append("No accuracy issues found")
        else:
            feedback["improvement_areas"].extend(issue_categories.keys())
            feedback["pattern_analysis"] = self._analyze_issue_patterns(
                issue_categories
            )

        return feedback

    def _categorize_issues(self, issues: List[str]) -> Dict[str, List[str]]:
        """Categorize issues by type."""
        categories = {
            "terminology": [],
            "statistics": [],
            "mechanics": [],
            "missing_info": [],
            "inconsistent_data": [],
        }

        for issue in issues:
            issue_lower = issue.lower()
            if any(
                term in issue_lower for term in ["should be", "terminology", "term"]
            ):
                categories["terminology"].append(issue)
            elif any(
                term in issue_lower for term in ["mismatch", "incorrect", "wrong"]
            ):
                categories["statistics"].append(issue)
            elif any(term in issue_lower for term in ["rule", "mechanics", "critical"]):
                categories["mechanics"].append(issue)
            elif any(term in issue_lower for term in ["missing", "not found"]):
                categories["missing_info"].append(issue)
            else:
                categories["inconsistent_data"].append(issue)

        return categories

    def _analyze_issue_patterns(
        self, issue_categories: Dict[str, List[str]]
    ) -> List[str]:
        """Analyze patterns in issue categories."""
        patterns = []

        if issue_categories["terminology"]:
            patterns.append(
                f"Frequent terminology issues ({len(issue_categories['terminology'])} found)"
            )

        if issue_categories["statistics"]:
            patterns.append(
                f"Statistical accuracy issues ({len(issue_categories['statistics'])} found)"
            )

        if issue_categories["mechanics"]:
            patterns.append(
                f"Rule mechanics misunderstandings ({len(issue_categories['mechanics'])} found)"
            )

        if issue_categories["missing_info"]:
            patterns.append(
                "Missing information in responses - consider more comprehensive answers"
            )

        return patterns

    def reset_metrics(self) -> None:
        """Reset validation metrics."""
        self.metrics = ValidationMetrics()
        self.logger.info("Validation metrics reset")

    def health_check(self) -> Dict[str, Any]:
        """Get health status of the AI Validation Service."""
        try:
            metrics = self.get_validation_metrics()

            return {
                "status": "healthy",
                "validation_rules_loaded": len(self.validation_rules),
                "terminology_rules_loaded": len(self.terminology_rules),
                "metrics": metrics,
                "last_check": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat(),
            }


# Global AI Validation Service instance
ai_validation_service = AIValidationService()
