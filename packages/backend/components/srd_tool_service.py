"""
SRD Tool Service for D&D 5.1 System Reference Document.

This module provides LangGraph tool integrations for SRD queries, enabling AI agents
to access deterministic D&D 5.1 rules information through structured tool calls.

Features:
- LangGraph tool implementations for SRD queries
- Tool selection logic and fallback mechanisms
- Integration with RulesEngine from Story 2.3.2
- Performance optimization and caching
- Error handling for rule query failures
"""

import json
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from dataclasses import dataclass

from packages.shared.models import RulesQuery, RulesResponse, ToolCall, ToolResult
from packages.backend.components.rules_engine import rules_engine
from packages.backend.components.srd_audit_service import srd_audit_service
from packages.shared.logging_config import get_logger


@dataclass
class ToolPerformanceMetrics:
    """Performance metrics for tool execution."""
    tool_name: str
    execution_time: float
    success: bool
    cache_hit: bool
    timestamp: datetime
    error_message: Optional[str] = None


class SRDToolService:
    """
    Service providing LangGraph tools for SRD queries.

    This service bridges the gap between AI agents and deterministic SRD rules,
    providing structured tool interfaces for monster, spell, and weapon queries.
    """

    def __init__(self):
        self.logger = get_logger(f"{__name__}.SRDToolService")
        self._tool_metrics: List[ToolPerformanceMetrics] = []
        self.max_metrics_history = 1000

        # Tool definitions for LangGraph
        self.tool_definitions = {
            "query_monster": self._get_monster_tool_definition(),
            "query_spell": self._get_spell_tool_definition(),
            "query_weapon": self._get_weapon_tool_definition(),
            "compare_entities": self._get_comparison_tool_definition()
        }

        self.logger.info("SRD Tool Service initialized", available_tools=list(self.tool_definitions.keys()))

    def _get_monster_tool_definition(self) -> Dict[str, Any]:
        """Get LangGraph tool definition for monster queries."""
        return {
            "name": "query_monster",
            "description": "Query detailed information about a D&D 5.1 SRD monster including combat statistics, abilities, and challenge rating.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the monster to query (e.g., 'Goblin', 'Orc', 'Dragon')"
                    },
                    "include_combat_stats": {
                        "type": "boolean",
                        "description": "Whether to include detailed combat statistics and analysis",
                        "default": True
                    },
                    "context": {
                        "type": "string",
                        "description": "Context for the query (e.g., 'encounter', 'character creation')",
                        "default": "general"
                    }
                },
                "required": ["name"]
            }
        }

    def _get_spell_tool_definition(self) -> Dict[str, Any]:
        """Get LangGraph tool definition for spell queries."""
        return {
            "name": "query_spell",
            "description": "Query detailed information about a D&D 5.1 SRD spell including mechanics, components, and effects.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the spell to query (e.g., 'Fire Bolt', 'Cure Wounds', 'Detect Magic')"
                    },
                    "include_mechanics": {
                        "type": "boolean",
                        "description": "Whether to include detailed spell mechanics analysis",
                        "default": True
                    },
                    "context": {
                        "type": "string",
                        "description": "Context for the query (e.g., 'combat', 'roleplay', 'character building')",
                        "default": "general"
                    }
                },
                "required": ["name"]
            }
        }

    def _get_weapon_tool_definition(self) -> Dict[str, Any]:
        """Get LangGraph tool definition for weapon queries."""
        return {
            "name": "query_weapon",
            "description": "Query detailed information about a D&D 5.1 SRD weapon including damage, properties, and combat analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the weapon to query (e.g., 'Longsword', 'Shortbow', 'Quarterstaff')"
                    },
                    "include_analysis": {
                        "type": "boolean",
                        "description": "Whether to include weapon effectiveness analysis and recommendations",
                        "default": True
                    },
                    "context": {
                        "type": "string",
                        "description": "Context for the query (e.g., 'character creation', 'encounter preparation')",
                        "default": "general"
                    }
                },
                "required": ["name"]
            }
        }

    def _get_comparison_tool_definition(self) -> Dict[str, Any]:
        """Get LangGraph tool definition for entity comparison."""
        return {
            "name": "compare_entities",
            "description": "Compare multiple D&D 5.1 SRD entities side-by-side for analysis and decision making.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_type": {
                        "type": "string",
                        "enum": ["monster", "spell", "weapon"],
                        "description": "Type of entities to compare"
                    },
                    "names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Names of entities to compare (2-5 entities)",
                        "minItems": 2,
                        "maxItems": 5
                    },
                    "comparison_focus": {
                        "type": "string",
                        "enum": ["combat", "roleplay", "optimization", "general"],
                        "description": "Focus area for comparison analysis",
                        "default": "general"
                    }
                },
                "required": ["entity_type", "names"]
            }
        }

    # LangGraph Tool Implementations
    async def query_monster_tool(self, name: str, include_combat_stats: bool = True, context: str = "general") -> Dict[str, Any]:
        """LangGraph tool for querying monster information."""
        start_time = time.time()

        try:
            # Create RulesEngine query
            query = RulesQuery(
                query_type="monster",
                name=name,
                context=context,
                filters={"include_combat_stats": include_combat_stats} if include_combat_stats else {}
            )

            # Execute query
            response = await rules_engine.query(query)

            # Calculate execution time
            execution_time = time.time() - start_time

            # Record metrics
            self._record_tool_metrics("query_monster", execution_time, response.found, False)

            # Format result for LangGraph
            result_data = {
                "tool_name": "query_monster",
                "success": response.found,
                "query": name,
                "execution_time": execution_time,
                "data": response.data if response.found else None,
                "error": response.error if not response.found else None
            }

            # Log audit event
            if response.found:
                srd_audit_service.log_data_access(
                    response.data, "tool_service", "ai_agent", "tool_query"
                )

            return result_data

        except Exception as e:
            execution_time = time.time() - start_time
            self._record_tool_metrics("query_monster", execution_time, False, False, str(e))

            return {
                "tool_name": "query_monster",
                "success": False,
                "query": name,
                "execution_time": execution_time,
                "error": f"Tool execution failed: {str(e)}"
            }

    async def query_spell_tool(self, name: str, include_mechanics: bool = True, context: str = "general") -> Dict[str, Any]:
        """LangGraph tool for querying spell information."""
        start_time = time.time()

        try:
            # Create RulesEngine query
            query = RulesQuery(
                query_type="spell",
                name=name,
                context=context,
                filters={"include_mechanics": include_mechanics} if include_mechanics else {}
            )

            # Execute query
            response = await rules_engine.query(query)

            # Calculate execution time
            execution_time = time.time() - start_time

            # Record metrics
            self._record_tool_metrics("query_spell", execution_time, response.found, False)

            # Format result for LangGraph
            result_data = {
                "tool_name": "query_spell",
                "success": response.found,
                "query": name,
                "execution_time": execution_time,
                "data": response.data if response.found else None,
                "error": response.error if not response.found else None
            }

            # Log audit event
            if response.found:
                srd_audit_service.log_data_access(
                    response.data, "tool_service", "ai_agent", "tool_query"
                )

            return result_data

        except Exception as e:
            execution_time = time.time() - start_time
            self._record_tool_metrics("query_spell", execution_time, False, False, str(e))

            return {
                "tool_name": "query_spell",
                "success": False,
                "query": name,
                "execution_time": execution_time,
                "error": f"Tool execution failed: {str(e)}"
            }

    async def query_weapon_tool(self, name: str, include_analysis: bool = True, context: str = "general") -> Dict[str, Any]:
        """LangGraph tool for querying weapon information."""
        start_time = time.time()

        try:
            # Create RulesEngine query
            query = RulesQuery(
                query_type="weapon",
                name=name,
                context=context,
                filters={"include_analysis": include_analysis} if include_analysis else {}
            )

            # Execute query
            response = await rules_engine.query(query)

            # Calculate execution time
            execution_time = time.time() - start_time

            # Record metrics
            self._record_tool_metrics("query_weapon", execution_time, response.found, False)

            # Format result for LangGraph
            result_data = {
                "tool_name": "query_weapon",
                "success": response.found,
                "query": name,
                "execution_time": execution_time,
                "data": response.data if response.found else None,
                "error": response.error if not response.found else None
            }

            # Log audit event
            if response.found:
                srd_audit_service.log_data_access(
                    response.data, "tool_service", "ai_agent", "tool_query"
                )

            return result_data

        except Exception as e:
            execution_time = time.time() - start_time
            self._record_tool_metrics("query_weapon", execution_time, False, False, str(e))

            return {
                "tool_name": "query_weapon",
                "success": False,
                "query": name,
                "execution_time": execution_time,
                "error": f"Tool execution failed: {str(e)}"
            }

    async def compare_entities_tool(self, entity_type: str, names: List[str], comparison_focus: str = "general") -> Dict[str, Any]:
        """LangGraph tool for comparing multiple entities."""
        start_time = time.time()

        try:
            comparison_results = []

            if entity_type == "monster":
                for name in names:
                    query = RulesQuery(query_type="monster", name=name, context="comparison")
                    response = await rules_engine.query(query)
                    if response.found:
                        comparison_results.append({
                            "name": name,
                            "data": response.data,
                            "found": True
                        })
                    else:
                        comparison_results.append({
                            "name": name,
                            "error": response.error,
                            "found": False
                        })

            elif entity_type == "spell":
                for name in names:
                    query = RulesQuery(query_type="spell", name=name, context="comparison")
                    response = await rules_engine.query(query)
                    if response.found:
                        comparison_results.append({
                            "name": name,
                            "data": response.data,
                            "found": True
                        })
                    else:
                        comparison_results.append({
                            "name": name,
                            "error": response.error,
                            "found": False
                        })

            elif entity_type == "weapon":
                for name in names:
                    query = RulesQuery(query_type="weapon", name=name, context="comparison")
                    response = await rules_engine.query(query)
                    if response.found:
                        comparison_results.append({
                            "name": name,
                            "data": response.data,
                            "found": True
                        })
                    else:
                        comparison_results.append({
                            "name": name,
                            "error": response.error,
                            "found": False
                        })

            # Calculate execution time
            execution_time = time.time() - start_time

            # Record metrics
            success_count = sum(1 for r in comparison_results if r["found"])
            self._record_tool_metrics("compare_entities", execution_time, success_count > 0, False)

            # Generate comparison analysis
            analysis = self._generate_comparison_analysis(entity_type, comparison_results, comparison_focus)

            return {
                "tool_name": "compare_entities",
                "success": success_count > 0,
                "entity_type": entity_type,
                "comparison_focus": comparison_focus,
                "execution_time": execution_time,
                "results": comparison_results,
                "analysis": analysis
            }

        except Exception as e:
            execution_time = time.time() - start_time
            self._record_tool_metrics("compare_entities", execution_time, False, False, str(e))

            return {
                "tool_name": "compare_entities",
                "success": False,
                "entity_type": entity_type,
                "execution_time": execution_time,
                "error": f"Comparison tool failed: {str(e)}"
            }

    def _generate_comparison_analysis(self, entity_type: str, results: List[Dict], focus: str) -> Dict[str, Any]:
        """Generate analysis for entity comparison."""
        found_results = [r for r in results if r["found"]]

        if not found_results:
            return {"summary": "No entities found for comparison"}

        analysis = {
            "total_requested": len(results),
            "total_found": len(found_results),
            "focus": focus,
            "summary": f"Comparison of {len(found_results)} {entity_type}(s)"
        }

        if entity_type == "monster" and focus == "combat":
            analysis["combat_analysis"] = self._analyze_monster_combat_comparison(found_results)
        elif entity_type == "spell" and focus == "optimization":
            analysis["spell_analysis"] = self._analyze_spell_optimization_comparison(found_results)
        elif entity_type == "weapon" and focus == "optimization":
            analysis["weapon_analysis"] = self._analyze_weapon_optimization_comparison(found_results)

        return analysis

    def _analyze_monster_combat_comparison(self, monsters: List[Dict]) -> Dict[str, Any]:
        """Analyze monster comparison for combat purposes."""
        if not monsters:
            return {}

        # Sort by challenge rating
        sorted_monsters = sorted(monsters, key=lambda x: x["data"].get("challenge_rating", "0"))

        return {
            "difficulty_progression": [m["name"] for m in sorted_monsters],
            "cr_range": f"{sorted_monsters[0]['data']['challenge_rating']} to {sorted_monsters[-1]['data']['challenge_rating']}",
            "recommendations": self._generate_monster_combat_recommendations(monsters)
        }

    def _analyze_spell_optimization_comparison(self, spells: List[Dict]) -> Dict[str, Any]:
        """Analyze spell comparison for optimization purposes."""
        if not spells:
            return {}

        # Group by level
        by_level = {}
        for spell in spells:
            level = spell["data"].get("level", 0)
            if level not in by_level:
                by_level[level] = []
            by_level[level].append(spell["name"])

        return {
            "level_distribution": by_level,
            "versatility_analysis": self._analyze_spell_versatility(spells)
        }

    def _analyze_weapon_optimization_comparison(self, weapons: List[Dict]) -> Dict[str, Any]:
        """Analyze weapon comparison for optimization purposes."""
        if not weapons:
            return {}

        # Analyze by damage type and properties
        damage_types = {}
        properties = {}

        for weapon in weapons:
            data = weapon["data"]
            damage_type = "Unknown"
            if "damage_type" in data:
                damage_type = data["damage_type"]
            if damage_type not in damage_types:
                damage_types[damage_type] = []
            damage_types[damage_type].append(weapon["name"])

            for prop in data.get("properties", []):
                if prop not in properties:
                    properties[prop] = []
                properties[prop].append(weapon["name"])

        return {
            "damage_type_distribution": damage_types,
            "property_analysis": properties,
            "optimization_recommendations": self._generate_weapon_optimization_recommendations(weapons)
        }

    def _generate_monster_combat_recommendations(self, monsters: List[Dict]) -> List[str]:
        """Generate combat recommendations for monster comparison."""
        recommendations = []

        if len(monsters) >= 2:
            recommendations.append("Consider encounter difficulty progression based on challenge ratings")

        # Check for ability score diversity
        ability_focuses = []
        for monster in monsters:
            data = monster["data"]
            if data.get("strength", 0) >= 16:
                ability_focuses.append(f"{monster['name']} (Strength)")
            if data.get("dexterity", 0) >= 16:
                ability_focuses.append(f"{monster['name']} (Dexterity)")
            if data.get("intelligence", 0) >= 14:
                ability_focuses.append(f"{monster['name']} (Intelligence)")

        if ability_focuses:
            recommendations.append(f"Combat focuses: {', '.join(ability_focuses)}")

        return recommendations

    def _analyze_spell_versatility(self, spells: List[Dict]) -> Dict[str, Any]:
        """Analyze spell versatility across different situations."""
        versatility = {
            "combat_spells": [],
            "utility_spells": [],
            "healing_spells": [],
            "control_spells": []
        }

        for spell in spells:
            name = spell["name"]
            data = spell["data"]

            # Simple categorization based on spell mechanics
            if "damage" in json.dumps(data).lower():
                versatility["combat_spells"].append(name)
            if "heal" in json.dumps(data).lower() or "cure" in json.dumps(data).lower():
                versatility["healing_spells"].append(name)
            if "control" in json.dumps(data).lower() or "charm" in json.dumps(data).lower():
                versatility["control_spells"].append(name)
            else:
                versatility["utility_spells"].append(name)

        return versatility

    def _generate_weapon_optimization_recommendations(self, weapons: List[Dict]) -> List[str]:
        """Generate weapon optimization recommendations."""
        recommendations = []

        if len(weapons) >= 2:
            recommendations.append("Consider weapon versatility and property combinations")

        # Check for damage type diversity
        damage_types = set()
        for weapon in weapons:
            data = weapon["data"]
            if "damage_type" in data:
                damage_types.add(data["damage_type"])

        if len(damage_types) > 1:
            recommendations.append(f"Good damage type diversity: {', '.join(damage_types)}")

        # Check for special properties
        special_props = []
        for weapon in weapons:
            data = weapon["data"]
            for prop in data.get("properties", []):
                if prop.lower() in ["finesse", "versatile", "reach", "two-handed"]:
                    special_props.append(f"{weapon['name']} ({prop})")

        if special_props:
            recommendations.append(f"Special properties: {', '.join(special_props)}")

        return recommendations

    def _record_tool_metrics(self, tool_name: str, execution_time: float, success: bool,
                            cache_hit: bool, error_message: Optional[str] = None) -> None:
        """Record tool execution metrics."""
        metrics = ToolPerformanceMetrics(
            tool_name=tool_name,
            execution_time=execution_time,
            success=success,
            cache_hit=cache_hit,
            timestamp=datetime.utcnow(),
            error_message=error_message
        )

        self._tool_metrics.append(metrics)

        # Maintain metrics history limit
        if len(self._tool_metrics) > self.max_metrics_history:
            self._tool_metrics = self._tool_metrics[-self.max_metrics_history:]

        # Log performance
        self.logger.info(
            "Tool execution metrics",
            tool_name=tool_name,
            execution_time=".4f",
            success=success,
            cache_hit=cache_hit
        )

        # Log slow executions (>100ms)
        if execution_time > 0.1:
            self.logger.warning(
                "Slow tool execution detected",
                tool_name=tool_name,
                execution_time=".4f"
            )

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available LangGraph tools."""
        return list(self.tool_definitions.values())

    def get_tool_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Get all tool definitions for LangGraph integration."""
        return self.tool_definitions

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for tool executions."""
        if not self._tool_metrics:
            return {"message": "No metrics available"}

        # Calculate statistics
        total_executions = len(self._tool_metrics)
        successful_executions = sum(1 for m in self._tool_metrics if m.success)
        total_execution_time = sum(m.execution_time for m in self._tool_metrics)
        avg_execution_time = total_execution_time / total_executions if total_executions > 0 else 0

        # Tool-specific stats
        tool_stats = {}
        for metrics in self._tool_metrics:
            if metrics.tool_name not in tool_stats:
                tool_stats[metrics.tool_name] = {
                    "count": 0,
                    "success_count": 0,
                    "total_time": 0.0,
                    "avg_time": 0.0
                }

            tool_stats[metrics.tool_name]["count"] += 1
            tool_stats[metrics.tool_name]["total_time"] += metrics.execution_time
            if metrics.success:
                tool_stats[metrics.tool_name]["success_count"] += 1

        # Calculate averages
        for tool_name, stats in tool_stats.items():
            if stats["count"] > 0:
                stats["avg_time"] = stats["total_time"] / stats["count"]
                stats["success_rate"] = stats["success_count"] / stats["count"]

        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "average_execution_time": avg_execution_time,
            "tool_stats": tool_stats,
            "slow_executions": sum(1 for m in self._tool_metrics if m.execution_time > 0.1)
        }

    def clear_metrics(self) -> None:
        """Clear all performance metrics."""
        self._tool_metrics.clear()
        self.logger.info("Tool performance metrics cleared")

    def health_check(self) -> Dict[str, Any]:
        """Get health status of the SRD Tool Service."""
        try:
            # Test RulesEngine connectivity
            rules_engine_health = rules_engine.health_check()

            # Get performance stats
            perf_stats = self.get_performance_stats()

            return {
                "status": "healthy" if rules_engine_health["status"] == "healthy" else "degraded",
                "rules_engine_connected": rules_engine_health["status"] == "healthy",
                "available_tools": len(self.tool_definitions),
                "metrics_recorded": len(self._tool_metrics),
                "performance_stats": perf_stats,
                "last_check": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }


# Global SRD Tool Service instance
srd_tool_service = SRDToolService()