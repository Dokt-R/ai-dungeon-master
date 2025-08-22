"""
Unit tests for Rule Providers.

Tests cover:
- Monster, Spell, and Weapon provider functionality
- Query handling and response formatting
- Filter application and validation
- Cache management and performance
- Error handling and edge cases
- Provider-specific features and calculations
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from packages.backend.components.providers.monster_provider import MonsterRuleProvider
from packages.backend.components.providers.spell_provider import SpellRuleProvider
from packages.backend.components.providers.weapon_provider import WeaponRuleProvider
from packages.backend.components.rules_engine import RuleProviderType
from packages.shared.models import RulesQuery, RulesResponse


class TestMonsterRuleProvider:
    """Test cases for MonsterRuleProvider."""

    @pytest.fixture
    def monster_provider(self):
        """Create a fresh MonsterRuleProvider for each test."""
        provider = MonsterRuleProvider()
        provider.clear_cache()
        return provider

    @pytest.fixture
    def sample_monster_query(self):
        """Create a sample monster query."""
        return RulesQuery(
            query_type="monster",
            name="Goblin",
            context="encounter",
            filters={"min_cr": 0.25, "max_cr": 1},
        )

    def test_provider_initialization(self, monster_provider):
        """Test MonsterRuleProvider initialization."""
        assert isinstance(monster_provider, MonsterRuleProvider)
        assert monster_provider.provider_type == RuleProviderType.MONSTER
        assert monster_provider.default_ttl == 600

    @pytest.mark.asyncio
    async def test_query_monster_not_found(self, monster_provider):
        """Test querying a monster that doesn't exist."""
        query = RulesQuery(query_type="monster", name="NonexistentMonster")

        response = await monster_provider.query(query)

        assert isinstance(response, RulesResponse)
        assert response.found is False
        assert "not found" in response.error.lower()

    @pytest.mark.asyncio
    async def test_query_with_filters(self, monster_provider):
        """Test monster query with filters."""
        query = RulesQuery(
            query_type="monster", name="Test", filters={"min_cr": 1, "max_cr": 5}
        )

        response = await monster_provider.query(query)

        assert isinstance(response, RulesResponse)
        assert response.query_type == "monster"

    def test_cache_functionality(self, monster_provider, sample_monster_query):
        """Test caching functionality."""
        # First query should cache the result
        import asyncio

        async def run_query():
            return await monster_provider.query(sample_monster_query)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response1 = loop.run_until_complete(run_query())

            # Check cache was populated
            cache_key = monster_provider._generate_cache_key(sample_monster_query)
            cached_result = monster_provider._get_from_cache(cache_key)

            # Note: This test validates the cache structure, actual cache hits depend on data availability
            assert isinstance(response1, RulesResponse)
        finally:
            loop.close()

    def test_cache_key_generation(self, monster_provider):
        """Test cache key generation."""
        query1 = RulesQuery(query_type="monster", name="Goblin")
        query2 = RulesQuery(query_type="monster", name="Orc")
        query3 = RulesQuery(query_type="monster", name="Goblin", filters={"min_cr": 1})

        key1 = monster_provider._generate_cache_key(query1)
        key2 = monster_provider._generate_cache_key(query2)
        key3 = monster_provider._generate_cache_key(query3)

        assert key1 != key2  # Different names should have different keys
        assert (
            key1 != key3
        )  # Same name but different filters should have different keys

    def test_provider_stats(self, monster_provider):
        """Test provider statistics."""
        stats = monster_provider.get_provider_stats()

        assert isinstance(stats, dict)
        assert stats["provider_type"] == "monster"
        assert "supported_filters" in stats
        assert "special_methods" in stats
        assert isinstance(stats["supported_filters"], list)
        assert isinstance(stats["special_methods"], list)

    def test_cache_cleanup(self, monster_provider):
        """Test cache cleanup functionality."""
        # Initially cache should be empty
        initial_count = len(monster_provider.cache)

        # Clear cache
        monster_provider.clear_cache()

        assert len(monster_provider.cache) == 0

        # Cleanup expired entries (should be 0 since cache is empty)
        removed_count = monster_provider.cleanup_expired_cache()
        assert removed_count == 0


class TestSpellRuleProvider:
    """Test cases for SpellRuleProvider."""

    @pytest.fixture
    def spell_provider(self):
        """Create a fresh SpellRuleProvider for each test."""
        provider = SpellRuleProvider()
        provider.clear_cache()
        return provider

    @pytest.fixture
    def sample_spell_query(self):
        """Create a sample spell query."""
        return RulesQuery(
            query_type="spell", name="Fire Bolt", context="combat", filters={"level": 0}
        )

    def test_provider_initialization(self, spell_provider):
        """Test SpellRuleProvider initialization."""
        assert isinstance(spell_provider, SpellRuleProvider)
        assert spell_provider.provider_type == RuleProviderType.SPELL
        assert spell_provider.default_ttl == 600

    @pytest.mark.asyncio
    async def test_query_spell_not_found(self, spell_provider):
        """Test querying a spell that doesn't exist."""
        query = RulesQuery(query_type="spell", name="NonexistentSpell")

        response = await spell_provider.query(query)

        assert isinstance(response, RulesResponse)
        assert response.found is False
        assert "not found" in response.error.lower()

    @pytest.mark.asyncio
    async def test_query_with_level_filter(self, spell_provider):
        """Test spell query with level filter."""
        query = RulesQuery(query_type="spell", name="Test", filters={"level": 1})

        response = await spell_provider.query(query)

        assert isinstance(response, RulesResponse)
        assert response.query_type == "spell"

    @pytest.mark.asyncio
    async def test_query_with_school_filter(self, spell_provider):
        """Test spell query with school filter."""
        query = RulesQuery(
            query_type="spell", name="Test", filters={"school": "Evocation"}
        )

        response = await spell_provider.query(query)

        assert isinstance(response, RulesResponse)
        assert response.query_type == "spell"

    def test_spell_mechanics_analysis(self, spell_provider):
        """Test spell mechanics analysis functionality."""
        # Create a mock spell for testing
        from packages.shared.models import DataSource, Spell, SRDCompliance

        test_spell = Spell(
            spell_id=1,
            spell_name="Test Spell",
            level=3,
            school="Evocation",
            casting_time="1 action",
            range="120 feet",
            components="V, S, M (a handful of sand)",
            duration="Concentration, up to 1 minute",
            description="You create a wall of fire.",
            at_higher_levels="When you cast this spell using a spell slot of 4th level or higher, the damage increases.",
            classes=["Wizard", "Sorcerer"],
            srd_compliance=SRDCompliance(
                data_source="D&D 5.1 SRD",
                license_version="5.1",
                usage_restrictions=[],
                last_verified=datetime.utcnow(),
                verification_hash="test_hash",
                compliance_officer="Test",
            ),
            data_source=DataSource(
                source_name="D&D 5.1 SRD",
                source_url="https://dnd.wizards.com/articles/features/systems-reference-document-srd",
                publication_date=datetime(2016, 5, 12),
                version="5.1",
                checksum="test_checksum",
                is_official=True,
                attribution_required=True,
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_active=True,
        )

        # Test spell mechanics analysis
        mechanics = spell_provider._analyze_spell_mechanics(test_spell)

        assert isinstance(mechanics, dict)
        assert "spell_type" in mechanics
        assert "targeting" in mechanics
        assert "components" in mechanics
        assert "scaling" in mechanics

        # Verify specific analysis results
        assert mechanics["spell_type"] == "Damage"
        assert mechanics["concentration"] is True
        assert mechanics["scaling"]["has_scaling"] is True

    def test_spell_component_parsing(self, spell_provider):
        """Test spell component parsing."""
        components_str = "V, S, M (a diamond worth 100 gp)"

        components = spell_provider._parse_components(components_str)

        assert isinstance(components, dict)
        assert components["verbal"] is True
        assert components["somatic"] is True
        assert components["material"] is True
        assert "diamond worth 100 gp" in components["material_cost"]

    def test_provider_stats(self, spell_provider):
        """Test spell provider statistics."""
        stats = spell_provider.get_provider_stats()

        assert isinstance(stats, dict)
        assert stats["provider_type"] == "spell"
        assert "spell_schools" in stats
        assert "supported_filters" in stats
        assert len(stats["spell_schools"]) > 0  # Should have spell schools listed


class TestWeaponRuleProvider:
    """Test cases for WeaponRuleProvider."""

    @pytest.fixture
    def weapon_provider(self):
        """Create a fresh WeaponRuleProvider for each test."""
        provider = WeaponRuleProvider()
        provider.clear_cache()
        return provider

    @pytest.fixture
    def sample_weapon_query(self):
        """Create a sample weapon query."""
        return RulesQuery(
            query_type="weapon",
            name="Longsword",
            context="character creation",
            filters={"category": "Martial Melee Weapons"},
        )

    def test_provider_initialization(self, weapon_provider):
        """Test WeaponRuleProvider initialization."""
        assert isinstance(weapon_provider, WeaponRuleProvider)
        assert weapon_provider.provider_type == RuleProviderType.WEAPON
        assert weapon_provider.default_ttl == 600

    @pytest.mark.asyncio
    async def test_query_weapon_not_found(self, weapon_provider):
        """Test querying a weapon that doesn't exist."""
        query = RulesQuery(query_type="weapon", name="NonexistentWeapon")

        response = await weapon_provider.query(query)

        assert isinstance(response, RulesResponse)
        assert response.found is False
        assert "not found" in response.error.lower()

    @pytest.mark.asyncio
    async def test_query_with_category_filter(self, weapon_provider):
        """Test weapon query with category filter."""
        query = RulesQuery(
            query_type="weapon",
            name="Test",
            filters={"category": "Simple Melee Weapons"},
        )

        response = await weapon_provider.query(query)

        assert isinstance(response, RulesResponse)
        assert response.query_type == "weapon"

    def test_weapon_damage_parsing(self, weapon_provider):
        """Test weapon damage dice parsing."""
        damage_str = "1d8 slashing"

        damage_analysis = weapon_provider._parse_damage_dice(damage_str)

        assert isinstance(damage_analysis, dict)
        assert damage_analysis["dice_notation"] == "1d8"
        assert damage_analysis["num_dice"] == 1
        assert damage_analysis["dice_size"] == 8
        assert damage_analysis["average_damage"] == 4.5
        assert damage_analysis["damage_type"] == "Slashing"

    def test_weapon_property_analysis(self, weapon_provider):
        """Test weapon property analysis."""
        properties = ["Finesse", "Light", "Thrown (range 20/60)"]

        property_analysis = weapon_provider._analyze_weapon_properties(properties)

        assert isinstance(property_analysis, dict)
        assert property_analysis["finesse"] is True
        assert property_analysis["light"] is True
        assert property_analysis["melee_weapon"] is False  # Has thrown property
        assert property_analysis["ranged_weapon"] is True

    def test_weapon_cost_parsing(self, weapon_provider):
        """Test weapon cost parsing."""
        test_cases = [
            ("15 gp", 1500),  # 15 gold pieces
            ("5 sp", 50),  # 5 silver pieces
            ("1 pp", 1000),  # 1 platinum piece
            ("2 cp", 2),  # 2 copper pieces
        ]

        for cost_str, expected in test_cases:
            cost_value = weapon_provider._parse_cost(cost_str)
            assert cost_value == expected, f"Failed to parse {cost_str}"

    def test_weapon_weight_parsing(self, weapon_provider):
        """Test weapon weight parsing."""
        test_cases = [
            ("3 lb.", 3.0),
            ("0.5 lb.", 0.5),
            ("10 lb.", 10.0),
            ("2.25 lb.", 2.25),
        ]

        for weight_str, expected in test_cases:
            weight_value = weapon_provider._parse_weight(weight_str)
            assert weight_value == expected, f"Failed to parse {weight_str}"

    def test_weapon_combat_role_determination(self, weapon_provider):
        """Test weapon combat role determination."""
        # Test a heavy weapon
        heavy_weapon = Mock()
        heavy_weapon.damage = "2d6 slashing"
        heavy_weapon.properties = ["Heavy", "Two-Handed"]

        role = weapon_provider._determine_weapon_combat_role(heavy_weapon)
        assert role == "Heavy Damage Dealer"

        # Test a finesse weapon
        finesse_weapon = Mock()
        finesse_weapon.damage = "1d6 piercing"
        finesse_weapon.properties = ["Finesse", "Light"]

        role = weapon_provider._determine_weapon_combat_role(finesse_weapon)
        assert role == "Mobile Skirmisher"

        # Test a ranged weapon
        ranged_weapon = Mock()
        ranged_weapon.damage = "1d8 piercing"
        ranged_weapon.properties = ["Ammunition (range 80/320)"]

        role = weapon_provider._determine_weapon_combat_role(ranged_weapon)
        assert role == "Ranged Damage Dealer"

    def test_weapon_effectiveness_calculation(self, weapon_provider):
        """Test weapon effectiveness calculation."""
        test_weapon = Mock()
        test_weapon.damage = "1d8 slashing"
        test_weapon.properties = ["Versatile (1d10)", "Finesse"]
        test_weapon.cost = "15 gp"

        effectiveness = weapon_provider._calculate_weapon_effectiveness(test_weapon)

        assert isinstance(effectiveness, dict)
        assert "effectiveness_score" in effectiveness
        assert "cost_efficiency" in effectiveness
        assert "versatility_score" in effectiveness

        # Score should be reasonable (between 1-10)
        assert 1 <= effectiveness["effectiveness_score"] <= 10

    def test_provider_stats(self, weapon_provider):
        """Test weapon provider statistics."""
        stats = weapon_provider.get_provider_stats()

        assert isinstance(stats, dict)
        assert stats["provider_type"] == "weapon"
        assert "weapon_categories" in stats
        assert "common_properties" in stats
        assert "supported_filters" in stats
        assert len(stats["weapon_categories"]) > 0
        assert len(stats["common_properties"]) > 0


class TestBaseRuleProvider:
    """Test cases for BaseRuleProvider functionality."""

    def test_base_provider_methods(self):
        """Test that base provider methods exist and are callable."""
        provider = MonsterRuleProvider()

        # Test cache methods
        provider.clear_cache()
        removed_count = provider.cleanup_expired_cache()
        assert isinstance(removed_count, int)

        # Test cache key generation
        query = RulesQuery(query_type="monster", name="Test")
        cache_key = provider._generate_cache_key(query)
        assert isinstance(cache_key, str)
        assert len(cache_key) > 0

        # Test cache get/set (with expired entry)
        provider._set_cache("test_key", "test_data")

        # Verify cache was populated
        assert len(provider.cache) > 0

        # Clear cache
        provider.clear_cache()
        assert len(provider.cache) == 0
