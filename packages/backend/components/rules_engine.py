"""
RulesEngine Component for D&D 5.1 System Reference Document.

This module provides deterministic SRD rule queries for the AI Dungeon Master system.
Implements a provider pattern for different rule types with caching and performance monitoring.

Features:
- Provider pattern for extensible rule queries
- In-memory caching with TTL policies
- Performance monitoring and metrics
- Database connection pooling
- Error handling and graceful degradation
"""

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from packages.backend.components.srd_audit_service import srd_audit_service
from packages.backend.components.srd_compliance_service import srd_compliance_service
from packages.backend.components.srd_database_manager import srd_database_manager
from packages.shared.logging_config import get_logger
from packages.shared.models import RulesQuery, RulesResponse


class RuleProviderType(Enum):
    """Types of rule providers."""

    MONSTER = "monster"
    SPELL = "spell"
    WEAPON = "weapon"
    ITEM = "item"


@dataclass
class CacheEntry:
    """Cache entry with TTL."""

    data: Any
    timestamp: datetime
    ttl_seconds: int

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return datetime.utcnow() - self.timestamp > timedelta(seconds=self.ttl_seconds)


@dataclass
class QueryMetrics:
    """Performance metrics for queries."""

    query_type: str
    provider_type: str
    query_time: float
    cache_hit: bool
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None


class BaseRuleProvider:
    """Base class for rule providers."""

    def __init__(self, provider_type: RuleProviderType):
        self.provider_type = provider_type
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.cache: Dict[str, CacheEntry] = {}
        self.default_ttl = 300  # 5 minutes

    async def query(self, query: RulesQuery) -> RulesResponse:
        """Query the provider for rules data."""
        start_time = time.time()

        try:
            # Check cache first
            cache_key = self._generate_cache_key(query)
            cached_result = self._get_from_cache(cache_key)

            if cached_result is not None:
                query_time = time.time() - start_time
                self._record_metrics(query.query_type, True, query_time, True)
                return cached_result

            # Perform database query
            result = await self._perform_query(query)

            # Cache the result
            self._set_cache(cache_key, result)

            query_time = time.time() - start_time
            self._record_metrics(query.query_type, False, query_time, True)

            return result

        except Exception as e:
            query_time = time.time() - start_time
            self._record_metrics(query.query_type, False, query_time, False, str(e))
            self.logger.error(f"Query failed for {query.name}", error=str(e))
            return RulesResponse(
                query_type=query.query_type,
                name=query.name,
                found=False,
                error=f"Query failed: {str(e)}",
                query_time=query_time,
            )

    async def _perform_query(self, query: RulesQuery) -> RulesResponse:
        """Perform the actual database query. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement _perform_query")

    def _generate_cache_key(self, query: RulesQuery) -> str:
        """Generate cache key for query."""
        filters_str = str(sorted(query.filters.items())) if query.filters else ""
        return f"{query.query_type}:{query.name}:{filters_str}"

    def _get_from_cache(self, key: str) -> Optional[RulesResponse]:
        """Get item from cache if valid."""
        if key in self.cache:
            entry = self.cache[key]
            if not entry.is_expired():
                return entry.data
            else:
                # Remove expired entry
                del self.cache[key]
        return None

    def _set_cache(self, key: str, data: RulesResponse) -> None:
        """Set item in cache."""
        self.cache[key] = CacheEntry(
            data=data, timestamp=datetime.utcnow(), ttl_seconds=self.default_ttl
        )

    def _record_metrics(
        self,
        query_type: str,
        cache_hit: bool,
        query_time: float,
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """Record performance metrics."""
        # Initialize counters if not exist
        if not hasattr(self, '_total_queries'):
            self._total_queries = 0
            self._cache_hits = 0
            self._cache_misses = 0

        # Update counters
        self._total_queries += 1
        if cache_hit:
            self._cache_hits += 1
        else:
            self._cache_misses += 1

        metrics = QueryMetrics(
            query_type=query_type,
            provider_type=self.provider_type.value,
            query_time=query_time,
            cache_hit=cache_hit,
            timestamp=datetime.utcnow(),
            success=success,
            error_message=error_message,
        )

        # Log metrics
        self.logger.info(
            "Query metrics",
            query_type=query_type,
            provider_type=self.provider_type.value,
            query_time=f"{query_time:.4f}s",
            cache_hit=cache_hit,
            success=success,
        )

    def clear_cache(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()
        self.logger.info("Cache cleared", provider_type=self.provider_type.value)

    def cleanup_expired_cache(self) -> int:
        """Remove expired cache entries. Returns number of entries removed."""
        expired_keys = [key for key, entry in self.cache.items() if entry.is_expired()]

        for key in expired_keys:
            del self.cache[key]

        if expired_keys:
            self.logger.info(
                "Expired cache entries removed",
                provider_type=self.provider_type.value,
                removed_count=len(expired_keys),
            )

        return len(expired_keys)

    def get_provider_stats(self) -> Dict[str, Any]:
        """Get provider statistics."""
        total_queries = getattr(self, '_total_queries', 0)
        cache_hits = getattr(self, '_cache_hits', 0)
        cache_misses = getattr(self, '_cache_misses', 0)

        return {
            "cache_entries": len(self.cache),
            "cache_ttl": self.default_ttl,
            "provider_type": self.provider_type.value,
            "supported_filters": ["name", "context"],
            "special_methods": ["query", "clear_cache", "cleanup_expired_cache"],
            "total_queries": total_queries,
            "cache_hit_rate": cache_hits / max(total_queries, 1),
        }


class MonsterRuleProvider(BaseRuleProvider):
    """Rule provider for monster data."""

    def __init__(self):
        super().__init__(RuleProviderType.MONSTER)

    async def _perform_query(self, query: RulesQuery) -> RulesResponse:
        """Query monster data from database."""
        try:
            # Get monster by name
            monster = srd_database_manager.get_monster_by_name(query.name)

            if monster:
                # Verify compliance
                compliance_result = srd_compliance_service.verify_data_compliance(
                    monster, "monster", "rules_engine"
                )

                if compliance_result.is_compliant:
                    # Log audit event
                    srd_audit_service.log_data_access(
                        monster, "rules_engine", "system", "query"
                    )

                    return RulesResponse(
                        query_type=query.query_type,
                        name=query.name,
                        found=True,
                        data=monster,
                        query_time=0.0,  # Will be set by parent method
                    )
                else:
                    return RulesResponse(
                        query_type=query.query_type,
                        name=query.name,
                        found=False,
                        error="Data compliance check failed",
                        query_time=0.0,
                    )
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


class SpellRuleProvider(BaseRuleProvider):
    """Rule provider for spell data."""

    def __init__(self):
        super().__init__(RuleProviderType.SPELL)

    async def _perform_query(self, query: RulesQuery) -> RulesResponse:
        """Query spell data from database."""
        try:
            # Search for spell by name across all levels
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
                # Verify compliance
                compliance_result = srd_compliance_service.verify_data_compliance(
                    spell, "spell", "rules_engine"
                )

                if compliance_result.is_compliant:
                    # Log audit event
                    srd_audit_service.log_data_access(
                        spell, "rules_engine", "system", "query"
                    )

                    return RulesResponse(
                        query_type=query.query_type,
                        name=query.name,
                        found=True,
                        data=spell,
                        query_time=0.0,  # Will be set by parent method
                    )
                else:
                    return RulesResponse(
                        query_type=query.query_type,
                        name=query.name,
                        found=False,
                        error="Data compliance check failed",
                        query_time=0.0,
                    )
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


class WeaponRuleProvider(BaseRuleProvider):
    """Rule provider for weapon data."""

    def __init__(self):
        super().__init__(RuleProviderType.WEAPON)

    async def _perform_query(self, query: RulesQuery) -> RulesResponse:
        """Query weapon data from database."""
        try:
            # Search for weapon by name across all categories
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
                # Verify compliance
                compliance_result = srd_compliance_service.verify_data_compliance(
                    weapon, "weapon", "rules_engine"
                )

                if compliance_result.is_compliant:
                    # Log audit event
                    srd_audit_service.log_data_access(
                        weapon, "rules_engine", "system", "query"
                    )

                    return RulesResponse(
                        query_type=query.query_type,
                        name=query.name,
                        found=True,
                        data=weapon,
                        query_time=0.0,  # Will be set by parent method
                    )
                else:
                    return RulesResponse(
                        query_type=query.query_type,
                        name=query.name,
                        found=False,
                        error="Data compliance check failed",
                        query_time=0.0,
                    )
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


class RulesEngine:
    """
    Main RulesEngine component for SRD queries.

    Provides a unified interface for querying D&D 5.1 SRD data with:
    - Provider pattern for extensibility
    - Caching for performance
    - Performance monitoring
    - Error handling and graceful degradation
    """

    def __init__(self):
        self.logger = get_logger(f"{__name__}.RulesEngine")
        self.providers: Dict[RuleProviderType, BaseRuleProvider] = {}
        self.metrics: List[QueryMetrics] = []
        self.max_metrics_history = 1000
        self.cache_cleanup_interval = 60  # seconds

        # Initialize providers
        self._initialize_providers()

        # Start background cache cleanup
        self._start_cache_cleanup_task()

        self.logger.info("RulesEngine initialized")

    def _initialize_providers(self) -> None:
        """Initialize rule providers."""
        self.providers[RuleProviderType.MONSTER] = MonsterRuleProvider()
        self.providers[RuleProviderType.SPELL] = SpellRuleProvider()
        self.providers[RuleProviderType.WEAPON] = WeaponRuleProvider()

        self.logger.info(
            "Rule providers initialized", provider_count=len(self.providers)
        )

    def _start_cache_cleanup_task(self) -> None:
        """Start background task for cache cleanup."""
        # In a real implementation, this would use asyncio.create_task()
        # For now, we'll implement a simple cleanup mechanism
        pass

    async def query(self, query: RulesQuery) -> RulesResponse:
        """Execute a rules query."""
        start_time = time.time()

        try:
            # Validate query
            if not query.name or query.name.strip() == "":
                return RulesResponse(
                    query_type=query.query_type,
                    name=query.name,
                    found=False,
                    error="Query name cannot be empty",
                    query_time=time.time() - start_time,
                )

            # Get appropriate provider
            provider_type = RuleProviderType(query.query_type)
            if provider_type not in self.providers:
                return RulesResponse(
                    query_type=query.query_type,
                    name=query.name,
                    found=False,
                    error=f"No provider available for query type: {query.query_type}",
                    query_time=time.time() - start_time,
                )

            provider = self.providers[provider_type]

            # Execute query
            result = await provider.query(query)

            # Update query time
            result.query_time = time.time() - start_time

            # Record metrics
            self._record_query_metrics(query, result)

            return result

        except Exception as e:
            query_time = time.time() - start_time
            self.logger.error("RulesEngine query failed", error=str(e))
            return RulesResponse(
                query_type=query.query_type,
                name=query.name,
                found=False,
                error=f"RulesEngine error: {str(e)}",
                query_time=query_time,
            )

    def _record_query_metrics(self, query: RulesQuery, result: RulesResponse) -> None:
        """Record query performance metrics."""
        # This would be used for monitoring and optimization
        # For now, we'll just log the performance
        if result.query_time > 0.1:  # Log slow queries (>100ms)
            self.logger.warning(
                "Slow query detected",
                query_type=query.query_type,
                query_name=query.name,
                query_time=f"{result.query_time:.4f}s",
            )

    async def query_monster(
        self, name: str, context: Optional[str] = None
    ) -> RulesResponse:
        """Query monster data by name."""
        query = RulesQuery(query_type="monster", name=name, context=context)
        return await self.query(query)

    async def query_spell(
        self, name: str, context: Optional[str] = None
    ) -> RulesResponse:
        """Query spell data by name."""
        query = RulesQuery(query_type="spell", name=name, context=context)
        return await self.query(query)

    async def query_weapon(
        self, name: str, context: Optional[str] = None
    ) -> RulesResponse:
        """Query weapon data by name."""
        query = RulesQuery(query_type="weapon", name=name, context=context)
        return await self.query(query)

    def clear_all_caches(self) -> Dict[str, int]:
        """Clear all provider caches. Returns count of cleared entries per provider."""
        cleared_counts = {}

        for provider_type, provider in self.providers.items():
            cleared_count = len(provider.cache)
            provider.clear_cache()
            cleared_counts[provider_type.value] = cleared_count

        self.logger.info("All caches cleared", cleared_counts=cleared_counts)
        return cleared_counts

    def cleanup_expired_caches(self) -> Dict[str, int]:
        """Clean up expired cache entries across all providers."""
        cleanup_counts = {}

        for provider_type, provider in self.providers.items():
            removed_count = provider.cleanup_expired_cache()
            cleanup_counts[provider_type.value] = removed_count

        if any(count > 0 for count in cleanup_counts.values()):
            self.logger.info(
                "Expired cache entries cleaned up", cleanup_counts=cleanup_counts
            )

        return cleanup_counts

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for all providers."""
        stats = {}

        for provider_type, provider in self.providers.items():
            stats[provider_type.value] = {
                "cache_entries": len(provider.cache),
                "default_ttl": provider.default_ttl,
            }

        return stats

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        # Calculate average query times by type
        query_times = {}
        cache_hits = {}

        for provider_type, provider in self.providers.items():
            # This would aggregate actual metrics if we were collecting them
            # For now, return basic stats
            query_times[provider_type.value] = 0.0
            cache_hits[provider_type.value] = 0.0

        return {
            "providers": list(self.providers.keys()),
            "cache_stats": self.get_cache_stats(),
            "average_query_times": query_times,
            "cache_hit_rates": cache_hits,
        }

    def health_check(self) -> Dict[str, Any]:
        """Get health status of the RulesEngine."""
        try:
            provider_status = {}
            for provider_type, provider in self.providers.items():
                provider_status[provider_type.value] = {
                    "healthy": True,
                    "cache_entries": len(provider.cache),
                }

            # Test database connectivity
            db_health = srd_database_manager.get_health_status()

            return {
                "status": "healthy" if db_health["status"] == "healthy" else "degraded",
                "providers": provider_status,
                "database_connected": db_health["status"] == "healthy",
                "cache_stats": self.get_cache_stats(),
                "last_check": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat(),
            }


# Global RulesEngine instance
rules_engine = RulesEngine()
