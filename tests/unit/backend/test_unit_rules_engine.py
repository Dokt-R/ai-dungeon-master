"""
Unit tests for RulesEngine Component.

Tests cover:
- RulesEngine initialization and provider management
- Query routing and response handling
- Performance monitoring and caching
- Error handling and graceful degradation
- Cache management and cleanup
- Health monitoring
"""

from datetime import datetime

import pytest

from packages.backend.components.providers.monster_provider import MonsterRuleProvider
from packages.backend.components.providers.spell_provider import SpellRuleProvider
from packages.backend.components.providers.weapon_provider import WeaponRuleProvider
from packages.backend.components.rules_engine import (
    QueryMetrics,
    RuleProviderType,
    RulesEngine,
)
from packages.shared.models import RulesQuery, RulesResponse


class TestRulesEngine:
    """Test cases for RulesEngine component."""

    @pytest.fixture
    def rules_engine(self):
        """Create a fresh RulesEngine for each test."""
        engine = RulesEngine()
        # Clear any existing cache
        engine.clear_all_caches()
        return engine

    @pytest.fixture
    def sample_query(self):
        """Create a sample rules query."""
        return RulesQuery(
            query_type="monster",
            name="Test Monster",
            context="combat encounter",
            filters={"min_cr": 1, "max_cr": 5},
        )

    def test_rules_engine_initialization(self, rules_engine):
        """Test RulesEngine initialization."""
        assert isinstance(rules_engine, RulesEngine)
        assert len(rules_engine.providers) == 3
        assert RuleProviderType.MONSTER in rules_engine.providers
        assert RuleProviderType.SPELL in rules_engine.providers
        assert RuleProviderType.WEAPON in rules_engine.providers

    def test_provider_initialization(self, rules_engine):
        """Test that providers are properly initialized."""
        assert isinstance(
            rules_engine.providers[RuleProviderType.MONSTER], MonsterRuleProvider
        )
        assert isinstance(
            rules_engine.providers[RuleProviderType.SPELL], SpellRuleProvider
        )
        assert isinstance(
            rules_engine.providers[RuleProviderType.WEAPON], WeaponRuleProvider
        )

    @pytest.mark.asyncio
    async def test_query_monster(self, rules_engine):
        """Test monster query functionality."""
        response = await rules_engine.query_monster("Goblin")

        assert isinstance(response, RulesResponse)
        assert response.query_type == "monster"
        assert response.name == "Goblin"
        assert response.query_time >= 0

    @pytest.mark.asyncio
    async def test_query_spell(self, rules_engine):
        """Test spell query functionality."""
        response = await rules_engine.query_spell("Fire Bolt")

        assert isinstance(response, RulesResponse)
        assert response.query_type == "spell"
        assert response.name == "Fire Bolt"
        assert response.query_time >= 0

    @pytest.mark.asyncio
    async def test_query_weapon(self, rules_engine):
        """Test weapon query functionality."""
        response = await rules_engine.query_weapon("Longsword")

        assert isinstance(response, RulesResponse)
        assert response.query_type == "weapon"
        assert response.name == "Longsword"
        assert response.query_time >= 0

    @pytest.mark.asyncio
    async def test_query_with_empty_name(self, rules_engine):
        """Test query with empty name."""
        query = RulesQuery(query_type="monster", name="")

        response = await rules_engine.query(query)

        assert isinstance(response, RulesResponse)
        assert response.found is False
        assert "empty" in response.error.lower()

    @pytest.mark.asyncio
    async def test_query_with_invalid_type(self, rules_engine):
        """Test query with invalid query type."""
        query = RulesQuery(query_type="invalid_type", name="Test")

        response = await rules_engine.query(query)

        assert isinstance(response, RulesResponse)
        assert response.found is False
        assert "provider" in response.error.lower()

    @pytest.mark.asyncio
    async def test_query_performance_monitoring(self, rules_engine):
        """Test that query performance is monitored."""
        query = RulesQuery(query_type="monster", name="Test Monster")

        start_time = datetime.utcnow()
        response = await rules_engine.query(query)
        end_time = datetime.utcnow()

        # Verify response structure
        assert isinstance(response, RulesResponse)
        assert response.query_time >= 0
        assert response.query_time <= (end_time - start_time).total_seconds()

    def test_cache_management(self, rules_engine):
        """Test cache management functionality."""
        # Clear caches
        cleared_counts = rules_engine.clear_all_caches()

        assert isinstance(cleared_counts, dict)
        assert len(cleared_counts) == 3  # Three providers
        assert all(isinstance(count, int) for count in cleared_counts.values())

    def test_cache_stats(self, rules_engine):
        """Test cache statistics retrieval."""
        stats = rules_engine.get_cache_stats()

        assert isinstance(stats, dict)
        assert len(stats) == 3  # Three providers

        for provider_stats in stats.values():
            assert "cache_entries" in provider_stats
            assert "default_ttl" in provider_stats
            assert isinstance(provider_stats["cache_entries"], int)
            assert isinstance(provider_stats["default_ttl"], int)

    def test_performance_stats(self, rules_engine):
        """Test performance statistics retrieval."""
        stats = rules_engine.get_performance_stats()

        assert isinstance(stats, dict)
        assert "providers" in stats
        assert "cache_stats" in stats
        assert len(stats["providers"]) == 3

    def test_health_check(self, rules_engine):
        """Test health check functionality."""
        health = rules_engine.health_check()

        assert isinstance(health, dict)
        assert "status" in health
        assert "providers" in health
        assert "cache_stats" in health
        assert "database_connected" in health
        assert "last_check" in health

    def test_cleanup_expired_caches(self, rules_engine):
        """Test expired cache cleanup."""
        cleanup_counts = rules_engine.cleanup_expired_caches()

        assert isinstance(cleanup_counts, dict)
        assert len(cleanup_counts) == 3  # Three providers
        assert all(isinstance(count, int) for count in cleanup_counts.values())

    @pytest.mark.asyncio
    async def test_concurrent_queries(self, rules_engine):
        """Test concurrent query handling."""
        import asyncio

        # Create multiple concurrent queries
        queries = [
            RulesQuery(query_type="monster", name="Goblin"),
            RulesQuery(query_type="spell", name="Fire Bolt"),
            RulesQuery(query_type="weapon", name="Longsword"),
        ]

        # Execute queries concurrently
        tasks = [rules_engine.query(query) for query in queries]
        responses = await asyncio.gather(*tasks)

        assert len(responses) == 3
        assert all(isinstance(response, RulesResponse) for response in responses)

    @pytest.mark.asyncio
    async def test_query_with_filters(self, rules_engine):
        """Test query with filters."""
        query = RulesQuery(
            query_type="monster", name="Test", filters={"min_cr": 1, "max_cr": 3}
        )

        response = await rules_engine.query(query)

        assert isinstance(response, RulesResponse)
        assert response.query_type == "monster"

    def test_provider_error_handling(self, rules_engine):
        """Test provider error handling."""
        # Test with a provider that might fail
        # This tests the error handling in the base provider class
        query = RulesQuery(query_type="monster", name="Nonexistent Monster")

        # The query should not raise an exception even if the monster is not found
        # It should return a proper RulesResponse with found=False
        import asyncio

        async def run_query():
            return await rules_engine.query(query)

        # This should complete without raising an exception
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(run_query())
            assert isinstance(response, RulesResponse)
        finally:
            loop.close()

    def test_cache_key_generation(self, rules_engine, sample_query):
        """Test cache key generation for queries."""
        # Test that the same query generates the same cache key
        provider = rules_engine.providers[RuleProviderType.MONSTER]

        key1 = provider._generate_cache_key(sample_query)
        key2 = provider._generate_cache_key(sample_query)

        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) > 0

    def test_cache_key_different_queries(self, rules_engine):
        """Test that different queries generate different cache keys."""
        query1 = RulesQuery(query_type="monster", name="Goblin")
        query2 = RulesQuery(query_type="monster", name="Orc")

        provider = rules_engine.providers[RuleProviderType.MONSTER]

        key1 = provider._generate_cache_key(query1)
        key2 = provider._generate_cache_key(query2)

        assert key1 != key2

    def test_cache_expiration(self, rules_engine):
        """Test cache entry expiration."""
        provider = rules_engine.providers[RuleProviderType.MONSTER]

        # Create a cache entry with very short TTL
        from datetime import timedelta

        from packages.backend.components.rules_engine import CacheEntry

        test_entry = CacheEntry(
            data="test_data",
            timestamp=datetime.utcnow() - timedelta(seconds=10),  # 10 seconds ago
            ttl_seconds=5,  # 5 second TTL
        )

        assert test_entry.is_expired() is True

    def test_metrics_recording(self, rules_engine):
        """Test metrics recording functionality."""
        # This would test the _record_query_metrics method
        # For now, we just test that the method exists and doesn't raise exceptions
        provider = rules_engine.providers[RuleProviderType.MONSTER]

        # This should not raise an exception
        provider._record_metrics("monster", False, 0.1, True)

    def test_provider_stats(self, rules_engine):
        """Test provider statistics retrieval."""
        for provider_type, provider in rules_engine.providers.items():
            stats = provider.get_provider_stats()

            assert isinstance(stats, dict)
            assert "cache_entries" in stats
            assert "cache_ttl" in stats
            assert "provider_type" in stats
            assert "supported_filters" in stats
            assert "special_methods" in stats


class TestRulesResponse:
    """Test cases for RulesResponse model."""

    def test_rules_response_creation(self):
        """Test RulesResponse creation."""
        response = RulesResponse(
            query_type="monster",
            name="Goblin",
            found=True,
            data={"test": "data"},
            query_time=0.123,
        )

        assert response.query_type == "monster"
        assert response.name == "Goblin"
        assert response.found is True
        assert response.data == {"test": "data"}
        assert response.query_time == 0.123
        assert response.error is None

    def test_rules_response_defaults(self):
        """Test RulesResponse default values."""
        response = RulesResponse()

        assert response.query_type is None
        assert response.name is None
        assert response.found is None
        assert response.data is None
        assert response.query_time is None
        assert response.error is None


class TestQueryMetrics:
    """Test cases for QueryMetrics model."""

    def test_query_metrics_creation(self):
        """Test QueryMetrics creation."""
        metrics = QueryMetrics(
            query_type="monster",
            provider_type="monster",
            query_time=0.123,
            cache_hit=False,
            timestamp=datetime.utcnow(),
            success=True,
        )

        assert metrics.query_type == "monster"
        assert metrics.provider_type == "monster"
        assert metrics.query_time == 0.123
        assert metrics.cache_hit is False
        assert metrics.success is True
        assert metrics.error_message is None
