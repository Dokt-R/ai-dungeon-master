"""
Spell Rule Provider for D&D 5.1 SRD RulesEngine.

This module provides spell-specific rule queries with caching and performance optimization.
Handles spell data retrieval, filtering, and advanced queries.

Features:
- Spell lookup by name and attributes
- Spell level filtering and classification
- Spell school and class filtering
- Spell mechanics and effects retrieval
- Caching for frequently queried spells
"""

from typing import Any, Dict, List, Optional

from packages.backend.components.rules_engine import BaseRuleProvider, RuleProviderType
from packages.backend.components.srd.srd_audit_service import srd_audit_service
from packages.backend.components.srd.srd_compliance_service import srd_compliance_service
from packages.backend.components.srd.srd_database_manager import srd_database_manager
from packages.shared.logging_config import get_logger
from packages.shared.models import RulesQuery, RulesResponse, Spell


class SpellRuleProvider(BaseRuleProvider):
    """Rule provider for spell data with specialized spell queries."""

    def __init__(self):
        super().__init__(RuleProviderType.SPELL)
        self.logger = get_logger(f"{__name__}.SpellRuleProvider")
        self.default_ttl = 600  # 10 minutes for spell data

    async def _perform_query(self, query: RulesQuery) -> RulesResponse:
        """Perform spell-specific database query."""
        try:
            # Handle different types of spell queries
            if query.filters:
                return await self._handle_filtered_query(query)
            else:
                return await self._handle_name_query(query)

        except Exception as e:
            return RulesResponse(
                query_type=query.query_type,
                name=query.name,
                found=False,
                error=f"Spell query failed: {str(e)}",
                query_time=0.0,
            )

    async def _handle_name_query(self, query: RulesQuery) -> RulesResponse:
        """Handle spell query by name."""
        try:
            # Search across all spell levels
            spell = None
            for level in range(10):  # 0-9 spell levels
                spells = srd_database_manager.get_spells_by_level(level)
                for s in spells:
                    if s.spell_name.lower() == query.name.lower():
                        spell = s
                        break
                if spell:
                    break

            if spell:
                return await self._process_spell_result(spell, query)
            else:
                return RulesResponse(
                    query_type=query.query_type,
                    name=query.name,
                    found=False,
                    error="Spell not found in SRD database",
                    query_time=0.0,
                )

        except Exception as e:
            return RulesResponse(
                query_type=query.query_type,
                name=query.name,
                found=False,
                error=f"Database query failed: {str(e)}",
                query_time=0.0,
            )

    async def _handle_filtered_query(self, query: RulesQuery) -> RulesResponse:
        """Handle spell query with filters."""
        try:
            filters = query.filters or {}

            # Handle level-specific queries
            if "level" in filters:
                level = int(filters["level"])
                spells = srd_database_manager.get_spells_by_level(level)
                filtered_spells = self._apply_additional_filters(spells, filters)

                return RulesResponse(
                    query_type=query.query_type,
                    name=query.name,
                    found=len(filtered_spells) > 0,
                    data=filtered_spells if filtered_spells else None,
                    query_time=0.0,
                )

            # Handle school-specific queries
            if "school" in filters:
                school_spells = await self._get_spells_by_school(filters["school"])
                filtered_spells = self._apply_additional_filters(school_spells, filters)

                return RulesResponse(
                    query_type=query.query_type,
                    name=query.name,
                    found=len(filtered_spells) > 0,
                    data=filtered_spells if filtered_spells else None,
                    query_time=0.0,
                )

            # Handle class-specific queries
            if "class" in filters:
                class_spells = await self._get_spells_by_class(filters["class"])
                filtered_spells = self._apply_additional_filters(class_spells, filters)

                return RulesResponse(
                    query_type=query.query_type,
                    name=query.name,
                    found=len(filtered_spells) > 0,
                    data=filtered_spells if filtered_spells else None,
                    query_time=0.0,
                )

            # Default to name-based search if no recognized filters
            return await self._handle_name_query(query)

        except Exception as e:
            return RulesResponse(
                query_type=query.query_type,
                name=query.name,
                found=False,
                error=f"Filtered query failed: {str(e)}",
                query_time=0.0,
            )

    async def _process_spell_result(
        self, spell: Spell, query: RulesQuery
    ) -> RulesResponse:
        """Process and validate spell query result."""
        try:
            # Verify compliance
            compliance_result = srd_compliance_service.verify_data_compliance(
                spell, "spell", "rules_engine"
            )

            if not compliance_result.is_compliant:
                return RulesResponse(
                    query_type=query.query_type,
                    name=query.name,
                    found=False,
                    error="Data compliance check failed",
                    query_time=0.0,
                )

            # Log audit event
            srd_audit_service.log_data_access(spell, "rules_engine", "system", "query")

            # Format spell data for response
            spell_data = self._format_spell_data(spell)

            return RulesResponse(
                query_type=query.query_type,
                name=query.name,
                found=True,
                data=spell_data,
                query_time=0.0,
            )

        except Exception as e:
            return RulesResponse(
                query_type=query.query_type,
                name=query.name,
                found=False,
                error=f"Spell data processing failed: {str(e)}",
                query_time=0.0,
            )

    def _format_spell_data(self, spell: Spell) -> Dict[str, Any]:
        """Format spell data for API response."""
        return {
            "id": spell.spell_id,
            "name": spell.spell_name,
            "level": spell.level,
            "school": spell.school,
            "casting_time": spell.casting_time,
            "range": spell.range,
            "components": spell.components,
            "duration": spell.duration,
            "description": spell.description,
            "at_higher_levels": spell.at_higher_levels,
            "classes": spell.classes,
            "source": spell.data_source.source_name,
            "compliance_status": spell.srd_compliance.data_source,
            "last_updated": spell.updated_at.isoformat(),
        }

    def _apply_additional_filters(
        self, spells: List[Spell], filters: Dict[str, Any]
    ) -> List[Spell]:
        """Apply additional filters to spell list."""
        filtered_spells = spells

        # Filter by school
        if "school" in filters:
            school_filter = filters["school"].lower()
            filtered_spells = [
                s for s in filtered_spells if s.school.lower() == school_filter
            ]

        # Filter by class
        if "class" in filters:
            class_filter = filters["class"].lower()
            filtered_spells = [
                s
                for s in filtered_spells
                if any(cls.lower() == class_filter for cls in s.classes)
            ]

        # Filter by casting time
        if "casting_time" in filters:
            time_filter = filters["casting_time"].lower()
            filtered_spells = [
                s for s in filtered_spells if time_filter in s.casting_time.lower()
            ]

        # Filter by range
        if "range" in filters:
            range_filter = filters["range"].lower()
            filtered_spells = [
                s for s in filtered_spells if range_filter in s.range.lower()
            ]

        # Filter by duration
        if "duration" in filters:
            duration_filter = filters["duration"].lower()
            filtered_spells = [
                s for s in filtered_spells if duration_filter in s.duration.lower()
            ]

        # Filter by name substring
        if "name_contains" in filters:
            name_filter = filters["name_contains"].lower()
            filtered_spells = [
                s for s in filtered_spells if name_filter in s.spell_name.lower()
            ]

        return filtered_spells

    # Specialized spell query methods
    async def get_spells_by_level(self, level: int) -> List[Dict[str, Any]]:
        """Get all spells of a specific level."""
        try:
            spells = srd_database_manager.get_spells_by_level(level)

            # Verify compliance for all spells
            compliant_spells = []
            for spell in spells:
                compliance_result = srd_compliance_service.verify_data_compliance(
                    spell, "spell", "rules_engine"
                )
                if compliance_result.is_compliant:
                    compliant_spells.append(self._format_spell_data(spell))

            return compliant_spells

        except Exception as e:
            self.logger.error(
                "Failed to get spells by level", level=level, error=str(e)
            )
            return []

    async def get_spells_by_school(self, school: str) -> List[Dict[str, Any]]:
        """Get all spells of a specific school."""
        try:
            # Get spells from all levels and filter by school
            all_spells = []
            for level in range(10):
                spells = srd_database_manager.get_spells_by_level(level)
                school_spells = [
                    s for s in spells if s.school.lower() == school.lower()
                ]
                all_spells.extend(school_spells)

            # Verify compliance for all spells
            compliant_spells = []
            for spell in all_spells:
                compliance_result = srd_compliance_service.verify_data_compliance(
                    spell, "spell", "rules_engine"
                )
                if compliance_result.is_compliant:
                    compliant_spells.append(self._format_spell_data(spell))

            return compliant_spells

        except Exception as e:
            self.logger.error(
                "Failed to get spells by school", school=school, error=str(e)
            )
            return []

    async def _get_spells_by_class(self, class_name: str) -> List[Spell]:
        """Get all spells available to a specific class."""
        try:
            # Get spells from all levels and filter by class
            all_spells = []
            for level in range(10):
                spells = srd_database_manager.get_spells_by_level(level)
                class_spells = [
                    s
                    for s in spells
                    if class_name.lower() in [cls.lower() for cls in s.classes]
                ]
                all_spells.extend(class_spells)

            return all_spells

        except Exception as e:
            self.logger.error(
                "Failed to get spells by class", class_name=class_name, error=str(e)
            )
            return []

    async def get_spells_by_class(self, class_name: str) -> List[Dict[str, Any]]:
        """Get all spells available to a specific class (public method)."""
        try:
            spells = await self._get_spells_by_class(class_name)

            # Verify compliance for all spells
            compliant_spells = []
            for spell in spells:
                compliance_result = srd_compliance_service.verify_data_compliance(
                    spell, "spell", "rules_engine"
                )
                if compliance_result.is_compliant:
                    compliant_spells.append(self._format_spell_data(spell))

            return compliant_spells

        except Exception as e:
            self.logger.error(
                "Failed to get spells by class", class_name=class_name, error=str(e)
            )
            return []

    async def get_spell_mechanics(self, spell_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed mechanics information for a spell."""
        try:
            # Find the spell
            spell = None
            for level in range(10):
                spells = srd_database_manager.get_spells_by_level(level)
                for s in spells:
                    if s.spell_name.lower() == spell_name.lower():
                        spell = s
                        break
                if spell:
                    break

            if not spell:
                return None

            # Verify compliance
            compliance_result = srd_compliance_service.verify_data_compliance(
                spell, "spell", "rules_engine"
            )

            if not compliance_result.is_compliant:
                return None

            # Analyze spell mechanics
            mechanics = self._analyze_spell_mechanics(spell)

            return {"spell": self._format_spell_data(spell), "mechanics": mechanics}

        except Exception as e:
            self.logger.error(
                "Failed to get spell mechanics", spell_name=spell_name, error=str(e)
            )
            return None

    def _analyze_spell_mechanics(self, spell: Spell) -> Dict[str, Any]:
        """Analyze and categorize spell mechanics."""
        mechanics = {
            "spell_type": self._categorize_spell_type(spell),
            "targeting": self._analyze_targeting(spell),
            "components": self._parse_components(spell.components),
            "scaling": self._analyze_scaling(spell),
            "damage_type": self._detect_damage_type(spell),
            "saving_throw": self._detect_saving_throw(spell),
            "concentration": "concentration" in spell.duration.lower(),
            "ritual": False,  # Would need additional data to determine
            "attack_type": self._determine_attack_type(spell),
        }

        return mechanics

    def _categorize_spell_type(self, spell: Spell) -> str:
        """Categorize spell by its primary function."""
        description_lower = spell.description.lower()

        # Check for damage first (highest priority for combat spells)
        if any(
            word in description_lower
            for word in [
                "damage",
                "hit",
                "attack",
                "fire",
                "cold",
                "lightning",
                "acid",
                "poison",
                "necrotic",
                "psychic",
                "radiant",
                "thunder",
                "force",
            ]
        ):
            return "Damage"
        elif any(word in description_lower for word in ["heal", "cure", "restore"]):
            return "Healing"
        elif any(
            word in description_lower for word in ["buff", "enhance", "protection"]
        ):
            return "Buff/Support"
        elif any(
            word in description_lower
            for word in ["control", "charm", "fear", "polymorph"]
        ):
            return "Control"
        elif any(word in description_lower for word in ["summon", "create", "conjure"]):
            return "Conjuration"
        elif any(
            word in description_lower for word in ["information", "detect", "see"]
        ):
            return "Information"
        else:
            return "Utility"

    def _analyze_targeting(self, spell: Spell) -> Dict[str, Any]:
        """Analyze spell targeting mechanics."""
        range_lower = spell.range.lower()

        return {
            "range_type": "Self"
            if "self" in range_lower
            else "Ranged"
            if "feet" in range_lower
            else "Touch"
            if "touch" in range_lower
            else "Other",
            "range_value": self._extract_range_value(spell.range),
            "area_effect": any(
                shape in range_lower
                for shape in ["sphere", "cube", "cone", "line", "cylinder"]
            ),
            "single_target": "creature" in range_lower
            and "creatures" not in range_lower,
            "multi_target": "creatures" in range_lower or "targets" in range_lower,
        }

    def _parse_components(self, components: str) -> Dict[str, Any]:
        """Parse spell components into structured data."""
        components_lower = components.lower()

        return {
            "verbal": "v" in components_lower,
            "somatic": "s" in components_lower,
            "material": "m" in components_lower,
            "concentration": "concentration" in components_lower,
            "material_cost": self._extract_material_cost(components),
        }

    def _analyze_scaling(self, spell: Spell) -> Dict[str, Any]:
        """Analyze spell scaling mechanics."""
        has_higher_levels = (
            spell.at_higher_levels and spell.at_higher_levels.strip() != ""
        )

        return {
            "has_scaling": has_higher_levels,
            "scaling_description": spell.at_higher_levels
            if has_higher_levels
            else None,
            "scaling_type": "damage"
            if has_higher_levels and "damage" in spell.at_higher_levels.lower()
            else "effect"
            if has_higher_levels
            else None,
        }

    def _detect_damage_type(self, spell: Spell) -> Optional[str]:
        """Detect spell damage type from description."""
        description_lower = spell.description.lower()

        damage_types = [
            "acid",
            "bludgeoning",
            "cold",
            "fire",
            "force",
            "lightning",
            "necrotic",
            "piercing",
            "poison",
            "psychic",
            "radiant",
            "slashing",
            "thunder",
        ]

        for damage_type in damage_types:
            if damage_type in description_lower:
                return damage_type.title()

        return None

    def _detect_saving_throw(self, spell: Spell) -> Optional[str]:
        """Detect saving throw from spell description."""
        description_lower = spell.description.lower()

        saving_throws = [
            "strength",
            "dexterity",
            "constitution",
            "intelligence",
            "wisdom",
            "charisma",
        ]

        for saving_throw in saving_throws:
            if f"{saving_throw} saving throw" in description_lower:
                return saving_throw.title()

        return None

    def _determine_attack_type(self, spell: Spell) -> Optional[str]:
        """Determine if spell involves an attack."""
        description_lower = spell.description.lower()

        if "spell attack" in description_lower:
            return "Spell Attack"
        elif "saving throw" in description_lower:
            return "Saving Throw"
        else:
            return "Automatic"

    def _extract_range_value(self, range_str: str) -> Optional[int]:
        """Extract numerical range value from range string."""
        import re

        match = re.search(r"(\d+)", range_str)
        return int(match.group(1)) if match else None

    def _extract_material_cost(self, components: str) -> Optional[str]:
        """Extract material component cost from components string."""
        if "m (" in components.lower():
            start = components.lower().find("m (") + 3
            end = components.find(")", start)
            if end > start:
                return components[start:end].strip()
        return None

    def get_provider_stats(self) -> Dict[str, Any]:
        """Get statistics specific to spell provider."""
        return {
            "cache_entries": len(self.cache),
            "cache_ttl": self.default_ttl,
            "provider_type": self.provider_type.value,
            "supported_filters": [
                "level",
                "school",
                "class",
                "casting_time",
                "range",
                "duration",
                "name_contains",
            ],
            "special_methods": [
                "get_spells_by_level",
                "get_spells_by_school",
                "get_spells_by_class",
                "get_spell_mechanics",
            ],
            "spell_schools": [
                "Abjuration",
                "Conjuration",
                "Divination",
                "Enchantment",
                "Evocation",
                "Illusion",
                "Necromancy",
                "Transmutation",
            ],
        }
