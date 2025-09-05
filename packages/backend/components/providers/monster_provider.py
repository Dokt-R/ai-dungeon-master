"""
Monster Rule Provider for D&D 5.1 SRD RulesEngine.

This module provides monster-specific rule queries with caching and performance optimization.
Handles monster data retrieval, filtering, and advanced queries.

Features:
- Monster lookup by name and attributes
- Challenge rating filtering
- Monster type and alignment queries
- Combat statistics retrieval
- Caching for frequently queried monsters
"""

from typing import Any, Dict, List, Optional

from packages.backend.components.rules_engine import BaseRuleProvider, RuleProviderType
from packages.backend.components.srd.srd_audit_service import srd_audit_service
from packages.backend.components.srd.srd_compliance_service import srd_compliance_service
from packages.backend.components.srd.srd_database_manager import srd_database_manager
from packages.shared.logging_config import get_logger
from packages.shared.models import Monster, RulesQuery, RulesResponse


class MonsterRuleProvider(BaseRuleProvider):
    """Rule provider for monster data with specialized monster queries."""

    def __init__(self):
        super().__init__(RuleProviderType.MONSTER)
        self.logger = get_logger(f"{__name__}.MonsterRuleProvider")
        self.default_ttl = 600  # 10 minutes for monster data

    async def _perform_query(self, query: RulesQuery) -> RulesResponse:
        """Perform monster-specific database query."""
        try:
            # Handle different types of monster queries
            if query.filters:
                return await self._handle_filtered_query(query)
            else:
                return await self._handle_name_query(query)

        except Exception as e:
            return RulesResponse(
                query_type=query.query_type,
                name=query.name,
                found=False,
                error=f"Monster query failed: {str(e)}",
                query_time=0.0,
            )

    async def _handle_name_query(self, query: RulesQuery) -> RulesResponse:
        """Handle monster query by name."""
        try:
            monster = srd_database_manager.get_monster_by_name(query.name)

            if monster:
                return await self._process_monster_result(monster, query)
            else:
                return RulesResponse(
                    query_type=query.query_type,
                    name=query.name,
                    found=False,
                    error="Monster not found in SRD database",
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
        """Handle monster query with filters."""
        try:
            filters = query.filters or {}

            # Handle challenge rating range queries
            if "min_cr" in filters or "max_cr" in filters:
                min_cr = float(filters.get("min_cr", 0))
                max_cr = float(filters.get("max_cr", 30))
                monsters = srd_database_manager.get_monsters_by_challenge_rating(
                    min_cr, max_cr
                )

                # Apply additional filters
                filtered_monsters = self._apply_additional_filters(monsters, filters)

                return RulesResponse(
                    query_type=query.query_type,
                    name=query.name,
                    found=len(filtered_monsters) > 0,
                    data=filtered_monsters if filtered_monsters else None,
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

    async def _process_monster_result(
        self, monster: Monster, query: RulesQuery
    ) -> RulesResponse:
        """Process and validate monster query result."""
        try:
            # Verify compliance
            compliance_result = srd_compliance_service.verify_data_compliance(
                monster, "monster", "rules_engine"
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
            srd_audit_service.log_data_access(
                monster, "rules_engine", "system", "query"
            )

            # Format monster data for response
            monster_data = self._format_monster_data(monster)

            return RulesResponse(
                query_type=query.query_type,
                name=query.name,
                found=True,
                data=monster_data,
                query_time=0.0,
            )

        except Exception as e:
            return RulesResponse(
                query_type=query.query_type,
                name=query.name,
                found=False,
                error=f"Monster data processing failed: {str(e)}",
                query_time=0.0,
            )

    def _format_monster_data(self, monster: Monster) -> Dict[str, Any]:
        """Format monster data for API response."""
        return {
            "id": monster.monster_id,
            "name": monster.monster_name,
            "armor_class": monster.armor_class,
            "hit_points": monster.hit_points,
            "ability_scores": {
                "strength": monster.strength,
                "dexterity": monster.dexterity,
                "constitution": monster.constitution,
                "intelligence": monster.intelligence,
                "wisdom": monster.wisdom,
                "charisma": monster.charisma,
            },
            "challenge_rating": monster.challenge_rating,
            "actions": monster.actions,
            "special_abilities": monster.special_abilities,
            "description": monster.description,
            "source": monster.data_source.source_name,
            "compliance_status": monster.srd_compliance.data_source,
            "last_updated": monster.updated_at.isoformat(),
        }

    def _apply_additional_filters(
        self, monsters: List[Monster], filters: Dict[str, Any]
    ) -> List[Monster]:
        """Apply additional filters to monster list."""
        filtered_monsters = monsters

        # Filter by ability score minimums
        if "min_strength" in filters:
            min_str = int(filters["min_strength"])
            filtered_monsters = [m for m in filtered_monsters if m.strength >= min_str]

        if "min_dexterity" in filters:
            min_dex = int(filters["min_dexterity"])
            filtered_monsters = [m for m in filtered_monsters if m.dexterity >= min_dex]

        # Filter by armor class range
        if "min_ac" in filters:
            min_ac = int(filters["min_ac"])
            filtered_monsters = [
                m for m in filtered_monsters if m.armor_class >= min_ac
            ]

        if "max_ac" in filters:
            max_ac = int(filters["max_ac"])
            filtered_monsters = [
                m for m in filtered_monsters if m.armor_class <= max_ac
            ]

        # Filter by name substring
        if "name_contains" in filters:
            name_filter = filters["name_contains"].lower()
            filtered_monsters = [
                m for m in filtered_monsters if name_filter in m.monster_name.lower()
            ]

        return filtered_monsters

    # Specialized monster query methods
    async def get_monsters_by_cr_range(
        self, min_cr: float, max_cr: float
    ) -> List[Dict[str, Any]]:
        """Get monsters within challenge rating range."""
        try:
            monsters = srd_database_manager.get_monsters_by_challenge_rating(
                min_cr, max_cr
            )

            # Verify compliance for all monsters
            compliant_monsters = []
            for monster in monsters:
                compliance_result = srd_compliance_service.verify_data_compliance(
                    monster, "monster", "rules_engine"
                )
                if compliance_result.is_compliant:
                    compliant_monsters.append(self._format_monster_data(monster))

            return compliant_monsters

        except Exception as e:
            self.logger.error("Failed to get monsters by CR range", error=str(e))
            return []

    async def get_monster_combat_stats(
        self, monster_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get detailed combat statistics for a monster."""
        try:
            monster = srd_database_manager.get_monster_by_name(monster_name)

            if not monster:
                return None

            # Verify compliance
            compliance_result = srd_compliance_service.verify_data_compliance(
                monster, "monster", "rules_engine"
            )

            if not compliance_result.is_compliant:
                return None

            # Calculate combat statistics
            combat_stats = self._calculate_combat_stats(monster)

            return {
                "monster": self._format_monster_data(monster),
                "combat_stats": combat_stats,
            }

        except Exception as e:
            self.logger.error("Failed to get monster combat stats", error=str(e))
            return None

    def _calculate_combat_stats(self, monster: Monster) -> Dict[str, Any]:
        """Calculate detailed combat statistics for a monster."""
        # Calculate modifiers
        strength_mod = (monster.strength - 10) // 2
        dexterity_mod = (monster.dexterity - 10) // 2

        # Calculate proficiency bonus (based on CR)
        cr_float = self._parse_challenge_rating(monster.challenge_rating)
        proficiency_bonus = self._calculate_proficiency_bonus(cr_float)

        # Calculate attack bonus (assuming strength-based attacks)
        attack_bonus = strength_mod + proficiency_bonus

        # Calculate damage per round (rough estimate)
        # This is a simplified calculation - in practice, this would be more complex
        damage_per_round = 0
        if monster.actions:
            # Very basic damage estimation from actions text
            if "hit" in monster.actions.lower() and "damage" in monster.actions.lower():
                # Extract damage dice from actions (simplified)
                damage_per_round = self._estimate_damage(monster.actions)

        return {
            "ability_modifiers": {
                "strength": strength_mod,
                "dexterity": dexterity_mod,
                "constitution": (monster.constitution - 10) // 2,
                "intelligence": (monster.intelligence - 10) // 2,
                "wisdom": (monster.wisdom - 10) // 2,
                "charisma": (monster.charisma - 10) // 2,
            },
            "proficiency_bonus": proficiency_bonus,
            "attack_bonus": attack_bonus,
            "estimated_damage_per_round": damage_per_round,
            "effective_hp": self._calculate_effective_hp(monster),
            "combat_role": self._determine_combat_role(monster),
        }

    def _parse_challenge_rating(self, cr: str) -> float:
        """Parse challenge rating string to float."""
        try:
            if "/" in cr:
                numerator, denominator = cr.split("/")
                return float(numerator) / float(denominator)
            else:
                return float(cr)
        except (ValueError, ZeroDivisionError):
            return 0.0

    def _calculate_proficiency_bonus(self, cr: float) -> int:
        """Calculate proficiency bonus based on challenge rating."""
        if cr == 0:
            return 2
        elif cr <= 4:
            return 2
        elif cr <= 8:
            return 3
        elif cr <= 12:
            return 4
        elif cr <= 16:
            return 5
        else:
            return 6

    def _estimate_damage(self, actions: str) -> int:
        """Estimate average damage per round from actions text."""
        # This is a simplified estimation - in practice, this would use more sophisticated parsing
        actions_lower = actions.lower()

        # Look for damage patterns
        if "1d4" in actions_lower:
            return 2  # Average of 1d4
        elif "1d6" in actions_lower:
            return 3  # Average of 1d6
        elif "1d8" in actions_lower:
            return 4  # Average of 1d8
        elif "1d10" in actions_lower:
            return 5  # Average of 1d10
        elif "1d12" in actions_lower:
            return 6  # Average of 1d12
        else:
            return 3  # Default estimate

    def _calculate_effective_hp(self, monster: Monster) -> int:
        """Calculate effective hit points considering constitution modifier."""
        try:
            # Parse hit points - could be "45 (7d8 + 14)" or just "45"
            if " (" in monster.hit_points:
                # Extract the average value
                hp_str = monster.hit_points.split(" (")[0]
                base_hp = int(hp_str)
            else:
                base_hp = int(monster.hit_points)

            # Add constitution modifier per hit die
            con_mod = (monster.constitution - 10) // 2
            # Estimate hit dice (rough calculation)
            estimated_hd = max(1, base_hp // 6)  # Rough estimate
            effective_hp = base_hp + (con_mod * estimated_hd)

            return max(1, effective_hp)

        except (ValueError, IndexError):
            return 1

    def _determine_combat_role(self, monster: Monster) -> str:
        """Determine the monster's likely combat role."""
        try:
            cr = self._parse_challenge_rating(monster.challenge_rating)

            # High armor class suggests tank/defensive role
            if monster.armor_class >= 18:
                return "Defender/Tank"
            # High damage output suggests damage dealer
            elif cr >= 5:
                return "Damage Dealer"
            # High spellcasting ability suggests controller
            elif (
                monster.intelligence >= 14
                or monster.wisdom >= 14
                or monster.charisma >= 14
            ):
                return "Controller/Support"
            # Default to balanced
            else:
                return "Balanced"

        except Exception:
            return "Unknown"

    def get_provider_stats(self) -> Dict[str, Any]:
        """Get statistics specific to monster provider."""
        return {
            "cache_entries": len(self.cache),
            "cache_ttl": self.default_ttl,
            "provider_type": self.provider_type.value,
            "supported_filters": [
                "min_cr",
                "max_cr",
                "min_strength",
                "min_dexterity",
                "min_ac",
                "max_ac",
                "name_contains",
            ],
            "special_methods": ["get_monsters_by_cr_range", "get_monster_combat_stats"],
        }
