"""
Weapon Rule Provider for D&D 5.1 SRD RulesEngine.

This module provides weapon-specific rule queries with caching and performance optimization.
Handles weapon data retrieval, filtering, and advanced queries.

Features:
- Weapon lookup by name and attributes
- Weapon category filtering
- Damage type and property analysis
- Equipment comparison and optimization
- Caching for frequently queried weapons
"""

from typing import Any, Dict, List

from packages.backend.components.rules_engine import BaseRuleProvider, RuleProviderType
from packages.backend.components.srd_audit_service import srd_audit_service
from packages.backend.components.srd_compliance_service import srd_compliance_service
from packages.backend.components.srd_database_manager import srd_database_manager
from packages.shared.logging_config import get_logger
from packages.shared.models import RulesQuery, RulesResponse, Weapon


class WeaponRuleProvider(BaseRuleProvider):
    """Rule provider for weapon data with specialized weapon queries."""

    def __init__(self):
        super().__init__(RuleProviderType.WEAPON)
        self.logger = get_logger(f"{__name__}.WeaponRuleProvider")
        self.default_ttl = 600  # 10 minutes for weapon data

    async def _perform_query(self, query: RulesQuery) -> RulesResponse:
        """Perform weapon-specific database query."""
        try:
            # Handle different types of weapon queries
            if query.filters:
                return await self._handle_filtered_query(query)
            else:
                return await self._handle_name_query(query)

        except Exception as e:
            return RulesResponse(
                query_type=query.query_type,
                name=query.name,
                found=False,
                error=f"Weapon query failed: {str(e)}",
                query_time=0.0,
            )

    async def _handle_name_query(self, query: RulesQuery) -> RulesResponse:
        """Handle weapon query by name."""
        try:
            # Search across all weapon categories
            weapon = None
            categories = [
                "Simple Melee Weapons",
                "Simple Ranged Weapons",
                "Martial Melee Weapons",
                "Martial Ranged Weapons",
            ]

            for category in categories:
                weapons = srd_database_manager.get_weapons_by_category(category)
                for w in weapons:
                    if w.weapon_name.lower() == query.name.lower():
                        weapon = w
                        break
                if weapon:
                    break

            if weapon:
                return await self._process_weapon_result(weapon, query)
            else:
                return RulesResponse(
                    query_type=query.query_type,
                    name=query.name,
                    found=False,
                    error="Weapon not found in SRD database",
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
        """Handle weapon query with filters."""
        try:
            filters = query.filters or {}

            # Handle category-specific queries
            if "category" in filters:
                weapons = srd_database_manager.get_weapons_by_category(
                    filters["category"]
                )
                filtered_weapons = self._apply_additional_filters(weapons, filters)

                return RulesResponse(
                    query_type=query.query_type,
                    name=query.name,
                    found=len(filtered_weapons) > 0,
                    data=filtered_weapons if filtered_weapons else None,
                    query_time=0.0,
                )

            # Handle damage type queries
            if "damage_type" in filters:
                damage_weapons = await self._get_weapons_by_damage_type(
                    filters["damage_type"]
                )
                filtered_weapons = self._apply_additional_filters(
                    damage_weapons, filters
                )

                return RulesResponse(
                    query_type=query.query_type,
                    name=query.name,
                    found=len(filtered_weapons) > 0,
                    data=filtered_weapons if filtered_weapons else None,
                    query_time=0.0,
                )

            # Handle property queries
            if "property" in filters:
                property_weapons = await self._get_weapons_by_property(
                    filters["property"]
                )
                filtered_weapons = self._apply_additional_filters(
                    property_weapons, filters
                )

                return RulesResponse(
                    query_type=query.query_type,
                    name=query.name,
                    found=len(filtered_weapons) > 0,
                    data=filtered_weapons if filtered_weapons else None,
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

    async def _process_weapon_result(
        self, weapon: Weapon, query: RulesQuery
    ) -> RulesResponse:
        """Process and validate weapon query result."""
        try:
            # Verify compliance
            compliance_result = srd_compliance_service.verify_data_compliance(
                weapon, "weapon", "rules_engine"
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
            srd_audit_service.log_data_access(weapon, "rules_engine", "system", "query")

            # Format weapon data for response
            weapon_data = self._format_weapon_data(weapon)

            return RulesResponse(
                query_type=query.query_type,
                name=query.name,
                found=True,
                data=weapon_data,
                query_time=0.0,
            )

        except Exception as e:
            return RulesResponse(
                query_type=query.query_type,
                name=query.name,
                found=False,
                error=f"Weapon data processing failed: {str(e)}",
                query_time=0.0,
            )

    def _format_weapon_data(self, weapon: Weapon) -> Dict[str, Any]:
        """Format weapon data for API response."""
        return {
            "id": weapon.weapon_id,
            "name": weapon.weapon_name,
            "category": weapon.category,
            "cost": weapon.cost,
            "damage": weapon.damage,
            "weight": weapon.weight,
            "properties": weapon.properties,
            "description": weapon.description,
            "source": weapon.data_source.source_name,
            "compliance_status": weapon.srd_compliance.data_source,
            "last_updated": weapon.updated_at.isoformat(),
        }

    def _apply_additional_filters(
        self, weapons: List[Weapon], filters: Dict[str, Any]
    ) -> List[Weapon]:
        """Apply additional filters to weapon list."""
        filtered_weapons = weapons

        # Filter by cost range
        if "min_cost" in filters:
            min_cost = self._parse_cost(filters["min_cost"])
            filtered_weapons = [
                w for w in filtered_weapons if self._parse_cost(w.cost) >= min_cost
            ]

        if "max_cost" in filters:
            max_cost = self._parse_cost(filters["max_cost"])
            filtered_weapons = [
                w for w in filtered_weapons if self._parse_cost(w.cost) <= max_cost
            ]

        # Filter by weight range
        if "min_weight" in filters:
            min_weight = float(filters["min_weight"])
            filtered_weapons = [
                w
                for w in filtered_weapons
                if self._parse_weight(w.weight) >= min_weight
            ]

        if "max_weight" in filters:
            max_weight = float(filters["max_weight"])
            filtered_weapons = [
                w
                for w in filtered_weapons
                if self._parse_weight(w.weight) <= max_weight
            ]

        # Filter by properties
        if "has_property" in filters:
            required_property = filters["has_property"].lower()
            filtered_weapons = [
                w
                for w in filtered_weapons
                if any(prop.lower() == required_property for prop in w.properties)
            ]

        # Filter by damage type
        if "damage_type" in filters:
            damage_type = filters["damage_type"].lower()
            filtered_weapons = [
                w for w in filtered_weapons if damage_type in w.damage.lower()
            ]

        # Filter by name substring
        if "name_contains" in filters:
            name_filter = filters["name_contains"].lower()
            filtered_weapons = [
                w for w in filtered_weapons if name_filter in w.weapon_name.lower()
            ]

        return filtered_weapons

    def _parse_cost(self, cost_str: str) -> float:
        """Parse cost string into numerical value (in copper pieces)."""
        cost_str = cost_str.lower().strip()

        # Handle different denominations
        if "cp" in cost_str:
            return float(cost_str.replace("cp", "").strip())
        elif "sp" in cost_str:
            return float(cost_str.replace("sp", "").strip()) * 10
        elif "gp" in cost_str:
            return float(cost_str.replace("gp", "").strip()) * 100
        elif "pp" in cost_str:
            return float(cost_str.replace("pp", "").strip()) * 1000
        else:
            # Try to extract numerical value
            import re

            match = re.search(r"(\d+(?:\.\d+)?)", cost_str)
            return float(match.group(1)) if match else 0.0

    def _parse_weight(self, weight_str: str) -> float:
        """Parse weight string into numerical value (in pounds)."""
        import re

        match = re.search(r"(\d+(?:\.\d+)?)", weight_str)
        return float(match.group(1)) if match else 0.0

    # Specialized weapon query methods
    async def get_weapons_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all weapons of a specific category."""
        try:
            weapons = srd_database_manager.get_weapons_by_category(category)

            # Verify compliance for all weapons
            compliant_weapons = []
            for weapon in weapons:
                compliance_result = srd_compliance_service.verify_data_compliance(
                    weapon, "weapon", "rules_engine"
                )
                if compliance_result.is_compliant:
                    compliant_weapons.append(self._format_weapon_data(weapon))

            return compliant_weapons

        except Exception as e:
            self.logger.error(
                "Failed to get weapons by category", category=category, error=str(e)
            )
            return []

    async def _get_weapons_by_damage_type(self, damage_type: str) -> List[Weapon]:
        """Get all weapons that deal a specific damage type."""
        try:
            # Get weapons from all categories and filter by damage type
            all_weapons = []
            categories = [
                "Simple Melee Weapons",
                "Simple Ranged Weapons",
                "Martial Melee Weapons",
                "Martial Ranged Weapons",
            ]

            for category in categories:
                weapons = srd_database_manager.get_weapons_by_category(category)
                type_weapons = [
                    w for w in weapons if damage_type.lower() in w.damage.lower()
                ]
                all_weapons.extend(type_weapons)

            return all_weapons

        except Exception as e:
            self.logger.error(
                "Failed to get weapons by damage type",
                damage_type=damage_type,
                error=str(e),
            )
            return []

    async def get_weapons_by_damage_type(
        self, damage_type: str
    ) -> List[Dict[str, Any]]:
        """Get all weapons that deal a specific damage type (public method)."""
        try:
            weapons = await self._get_weapons_by_damage_type(damage_type)

            # Verify compliance for all weapons
            compliant_weapons = []
            for weapon in weapons:
                compliance_result = srd_compliance_service.verify_data_compliance(
                    weapon, "weapon", "rules_engine"
                )
                if compliance_result.is_compliant:
                    compliant_weapons.append(self._format_weapon_data(weapon))

            return compliant_weapons

        except Exception as e:
            self.logger.error(
                "Failed to get weapons by damage type",
                damage_type=damage_type,
                error=str(e),
            )
            return []

    async def _get_weapons_by_property(self, property_name: str) -> List[Weapon]:
        """Get all weapons with a specific property."""
        try:
            # Get weapons from all categories and filter by property
            all_weapons = []
            categories = [
                "Simple Melee Weapons",
                "Simple Ranged Weapons",
                "Martial Melee Weapons",
                "Martial Ranged Weapons",
            ]

            for category in categories:
                weapons = srd_database_manager.get_weapons_by_category(category)
                property_weapons = [
                    w
                    for w in weapons
                    if any(
                        prop.lower() == property_name.lower() for prop in w.properties
                    )
                ]
                all_weapons.extend(property_weapons)

            return all_weapons

        except Exception as e:
            self.logger.error(
                "Failed to get weapons by property",
                property_name=property_name,
                error=str(e),
            )
            return []

    async def get_weapons_by_property(self, property_name: str) -> List[Dict[str, Any]]:
        """Get all weapons with a specific property (public method)."""
        try:
            weapons = await self._get_weapons_by_property(property_name)

            # Verify compliance for all weapons
            compliant_weapons = []
            for weapon in weapons:
                compliance_result = srd_compliance_service.verify_data_compliance(
                    weapon, "weapon", "rules_engine"
                )
                if compliance_result.is_compliant:
                    compliant_weapons.append(self._format_weapon_data(weapon))

            return compliant_weapons

        except Exception as e:
            self.logger.error(
                "Failed to get weapons by property",
                property_name=property_name,
                error=str(e),
            )
            return []

    async def get_weapon_comparison(
        self, weapon_names: List[str]
    ) -> List[Dict[str, Any]]:
        """Compare multiple weapons side by side."""
        try:
            comparison_data = []

            for weapon_name in weapon_names:
                # Find the weapon
                weapon = None
                categories = [
                    "Simple Melee Weapons",
                    "Simple Ranged Weapons",
                    "Martial Melee Weapons",
                    "Martial Ranged Weapons",
                ]

                for category in categories:
                    weapons = srd_database_manager.get_weapons_by_category(category)
                    for w in weapons:
                        if w.weapon_name.lower() == weapon_name.lower():
                            weapon = w
                            break
                    if weapon:
                        break

                if weapon:
                    # Verify compliance
                    compliance_result = srd_compliance_service.verify_data_compliance(
                        weapon, "weapon", "rules_engine"
                    )

                    if compliance_result.is_compliant:
                        # Analyze weapon stats
                        weapon_analysis = self._analyze_weapon_stats(weapon)
                        comparison_data.append(
                            {
                                "weapon": self._format_weapon_data(weapon),
                                "analysis": weapon_analysis,
                            }
                        )

            return comparison_data

        except Exception as e:
            self.logger.error(
                "Failed to get weapon comparison",
                weapon_names=weapon_names,
                error=str(e),
            )
            return []

    def _analyze_weapon_stats(self, weapon: Weapon) -> Dict[str, Any]:
        """Analyze weapon statistics for comparison."""
        # Parse damage dice
        damage_analysis = self._parse_damage_dice(weapon.damage)

        # Analyze properties
        property_analysis = self._analyze_weapon_properties(weapon.properties)

        # Calculate effectiveness metrics
        effectiveness = self._calculate_weapon_effectiveness(weapon)

        return {
            "damage_analysis": damage_analysis,
            "property_analysis": property_analysis,
            "effectiveness_metrics": effectiveness,
            "combat_role": self._determine_weapon_combat_role(weapon),
        }

    def _parse_damage_dice(self, damage_str: str) -> Dict[str, Any]:
        """Parse weapon damage dice string."""
        import re

        # Extract dice pattern like "1d8" or "2d6"
        dice_match = re.search(r"(\d+)d(\d+)", damage_str)
        if dice_match:
            num_dice = int(dice_match.group(1))
            dice_size = int(dice_match.group(2))
            average_damage = (num_dice * (dice_size + 1)) / 2
        else:
            num_dice = 0
            dice_size = 0
            average_damage = 0

        # Extract damage type
        damage_type_match = re.search(
            r"(slashing|piercing|bludgeoning|acid|cold|fire|force|lightning|necrotic|poison|psychic|radiant|thunder)",
            damage_str.lower(),
        )
        damage_type = (
            damage_type_match.group(1).title() if damage_type_match else "Unknown"
        )

        return {
            "dice_notation": f"{num_dice}d{dice_size}" if num_dice > 0 else "N/A",
            "num_dice": num_dice,
            "dice_size": dice_size,
            "average_damage": average_damage,
            "damage_type": damage_type,
        }

    def _analyze_weapon_properties(self, properties: List[str]) -> Dict[str, Any]:
        """Analyze weapon properties for tactical implications."""
        analysis = {
            "melee_weapon": False,
            "ranged_weapon": False,
            "finesse": False,
            "light": False,
            "heavy": False,
            "two_handed": False,
            "versatile": False,
            "reach": False,
            "loading": False,
            "ammunition": False,
            "thrown": False,
            "special_properties": [],
        }

        for prop in properties:
            prop_lower = prop.lower()

            if "finesse" in prop_lower:
                analysis["finesse"] = True
            elif "light" in prop_lower:
                analysis["light"] = True
            elif "heavy" in prop_lower:
                analysis["heavy"] = True
            elif "two-handed" in prop_lower or "two handed" in prop_lower:
                analysis["two_handed"] = True
            elif "versatile" in prop_lower:
                analysis["versatile"] = True
            elif "reach" in prop_lower:
                analysis["reach"] = True
            elif "loading" in prop_lower:
                analysis["loading"] = True
            elif "ammunition" in prop_lower:
                analysis["ammunition"] = True
            elif "thrown" in prop_lower:
                analysis["thrown"] = True
            else:
                analysis["special_properties"].append(prop)

        # Determine weapon type based on category and properties
        # A weapon is melee if it's not ammunition-based and not thrown
        analysis["melee_weapon"] = not analysis["ammunition"] and not analysis["thrown"]
        analysis["ranged_weapon"] = analysis["ammunition"] or analysis["thrown"]

        return analysis

    def _calculate_weapon_effectiveness(self, weapon: Weapon) -> Dict[str, Any]:
        """Calculate weapon effectiveness metrics."""
        damage_analysis = self._parse_damage_dice(weapon.damage)
        property_analysis = self._analyze_weapon_properties(weapon.properties)

        # Simple effectiveness scoring (1-10 scale)
        effectiveness_score = 5  # Base score

        # Damage scoring
        if damage_analysis["average_damage"] > 10:
            effectiveness_score += 2
        elif damage_analysis["average_damage"] > 5:
            effectiveness_score += 1

        # Property bonuses
        if property_analysis["finesse"]:
            effectiveness_score += 1
        if property_analysis["versatile"]:
            effectiveness_score += 1
        if property_analysis["reach"]:
            effectiveness_score += 1
        if property_analysis["light"]:
            effectiveness_score += 0.5

        # Property penalties
        if property_analysis["heavy"]:
            effectiveness_score -= 1
        if property_analysis["loading"]:
            effectiveness_score -= 1
        if property_analysis["two_handed"]:
            effectiveness_score -= 0.5

        # Cost efficiency (higher cost reduces score)
        cost_gp = self._parse_cost(weapon.cost) / 100  # Convert to gold pieces
        if cost_gp > 50:
            effectiveness_score -= 2
        elif cost_gp > 25:
            effectiveness_score -= 1

        effectiveness_score = max(1, min(10, effectiveness_score))

        return {
            "effectiveness_score": effectiveness_score,
            "cost_efficiency": damage_analysis["average_damage"] / max(cost_gp, 0.1),
            "versatility_score": len(
                [
                    p
                    for p in weapon.properties
                    if p.lower() in ["finesse", "versatile", "light"]
                ]
            ),
        }

    def _determine_weapon_combat_role(self, weapon: Weapon) -> str:
        """Determine the weapon's typical combat role."""
        property_analysis = self._analyze_weapon_properties(weapon.properties)

        if property_analysis["ranged_weapon"]:
            # Check if any property contains "ammunition" (case-insensitive)
            if any("ammunition" in p.lower() for p in weapon.properties):
                return "Ranged Damage Dealer"
            else:
                return "Light Ranged Support"
        else:
            damage_analysis = self._parse_damage_dice(weapon.damage)

            if property_analysis["reach"]:
                return "Defensive Controller"
            elif property_analysis["heavy"]:
                return "Heavy Damage Dealer"
            elif property_analysis["light"] and property_analysis["finesse"]:
                return "Mobile Skirmisher"
            elif property_analysis["versatile"]:
                return "Flexible Combatant"
            elif damage_analysis["average_damage"] > 8:
                return "Damage Dealer"
            else:
                return "Balanced Combatant"

    def get_provider_stats(self) -> Dict[str, Any]:
        """Get statistics specific to weapon provider."""
        return {
            "cache_entries": len(self.cache),
            "cache_ttl": self.default_ttl,
            "provider_type": self.provider_type.value,
            "supported_filters": [
                "category",
                "damage_type",
                "property",
                "min_cost",
                "max_cost",
                "min_weight",
                "max_weight",
                "has_property",
                "name_contains",
            ],
            "special_methods": [
                "get_weapons_by_category",
                "get_weapons_by_damage_type",
                "get_weapons_by_property",
                "get_weapon_comparison",
            ],
            "weapon_categories": [
                "Simple Melee Weapons",
                "Simple Ranged Weapons",
                "Martial Melee Weapons",
                "Martial Ranged Weapons",
            ],
            "common_properties": [
                "Finesse",
                "Light",
                "Heavy",
                "Two-Handed",
                "Versatile",
                "Reach",
                "Loading",
                "Ammunition",
                "Thrown",
            ],
        }
