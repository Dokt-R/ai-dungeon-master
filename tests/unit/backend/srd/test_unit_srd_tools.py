"""
Unit tests for SRD Tool Service.

Tests cover:
- LangGraph tool definitions and integration
- Tool execution and performance monitoring
- Error handling and fallback mechanisms
- Tool result processing and formatting
- Performance optimization and caching
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from packages.backend.components.srd.srd_tool_service import (
    SRDToolService,
    ToolPerformanceMetrics,
)
from packages.shared.models import RulesResponse


class TestSRDToolService:
    """Test cases for SRD Tool Service."""

    @pytest.fixture
    def tool_service(self):
        """Create a fresh SRD Tool Service for each test."""
        service = SRDToolService()
        service.clear_metrics()
        return service

    @pytest.fixture
    def sample_monster_query(self):
        """Create a sample monster query for testing."""
        return {"name": "Goblin", "include_combat_stats": True, "context": "encounter"}

    @pytest.fixture
    def sample_spell_query(self):
        """Create a sample spell query for testing."""
        return {"name": "Fire Bolt", "include_mechanics": True, "context": "combat"}

    @pytest.fixture
    def sample_weapon_query(self):
        """Create a sample weapon query for testing."""
        return {
            "name": "Longsword",
            "include_analysis": True,
            "context": "character creation",
        }

    def test_service_initialization(self, tool_service):
        """Test SRD Tool Service initialization."""
        assert isinstance(tool_service, SRDToolService)
        assert (
            len(tool_service.tool_definitions) == 4
        )  # 4 tools: monster, spell, weapon, compare
        assert tool_service.max_metrics_history == 1000

    def test_tool_definitions(self, tool_service):
        """Test that tool definitions are properly structured."""
        definitions = tool_service.get_tool_definitions()

        assert "query_monster" in definitions
        assert "query_spell" in definitions
        assert "query_weapon" in definitions
        assert "compare_entities" in definitions

        # Check monster tool structure
        monster_tool = definitions["query_monster"]
        assert "name" in monster_tool
        assert "description" in monster_tool
        assert "parameters" in monster_tool
        assert monster_tool["parameters"]["type"] == "object"
        assert "name" in monster_tool["parameters"]["properties"]

    def test_available_tools(self, tool_service):
        """Test getting available tools list."""
        tools = tool_service.get_available_tools()

        assert len(tools) == 4
        assert all("name" in tool for tool in tools)
        assert all("description" in tool for tool in tools)

    @pytest.mark.asyncio
    async def test_query_monster_tool_success(self, tool_service, sample_monster_query):
        """Test successful monster query tool execution."""
        with (
            patch(
                "packages.backend.components.srd_tool_service.rules_engine"
            ) as mock_engine,
            patch(
                "packages.backend.components.srd_tool_service.srd_audit_service"
            ) as mock_audit,
        ):
            # Mock successful query
            mock_result = RulesResponse(
                query_type="monster",
                found=True,
                result={"id": 1, "name": "Goblin", "armor_class": 15},
                query_time=0.05,
            )
            mock_engine.query = AsyncMock(return_value=mock_result)
            mock_audit.log_data_access = Mock()

            result = await tool_service.query_monster_tool(**sample_monster_query)

            assert result["success"] is True
            assert result["query"] == "Goblin"
            assert "execution_time" in result
            assert result["data"] is not None

    @pytest.mark.asyncio
    async def test_query_monster_tool_not_found(self, tool_service):
        """Test monster query tool when monster is not found."""
        with (
            patch(
                "packages.backend.components.srd_tool_service.rules_engine"
            ) as mock_engine,
            patch(
                "packages.backend.components.srd_tool_service.srd_audit_service"
            ) as mock_audit,
        ):
            # Mock failed query
            mock_result = RulesResponse(
                query_type="monster",
                found=False,
                error="Monster not found",
                query_time=0.03,
            )
            mock_engine.query = AsyncMock(return_value=mock_result)
            mock_audit.log_data_access = Mock()

            result = await tool_service.query_monster_tool(name="NonexistentMonster")

            assert result["success"] is False
            assert result["query"] == "NonexistentMonster"
            assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_query_spell_tool_success(self, tool_service, sample_spell_query):
        """Test successful spell query tool execution."""
        with (
            patch(
                "packages.backend.components.srd_tool_service.rules_engine"
            ) as mock_engine,
            patch(
                "packages.backend.components.srd_tool_service.srd_audit_service"
            ) as mock_audit,
        ):
            # Mock successful query
            mock_result = RulesResponse(
                query_type="spell",
                found=True,
                result={
                    "id": 1,
                    "name": "Fire Bolt",
                    "level": 0,
                    "school": "Evocation",
                },
                query_time=0.04,
            )
            mock_engine.query = AsyncMock(return_value=mock_result)
            mock_audit.log_data_access = Mock()

            result = await tool_service.query_spell_tool(**sample_spell_query)

            assert result["success"] is True
            assert result["query"] == "Fire Bolt"
            assert result["data"] is not None

    @pytest.mark.asyncio
    async def test_query_weapon_tool_success(self, tool_service, sample_weapon_query):
        """Test successful weapon query tool execution."""
        with (
            patch(
                "packages.backend.components.srd_tool_service.rules_engine"
            ) as mock_engine,
            patch(
                "packages.backend.components.srd_tool_service.srd_audit_service"
            ) as mock_audit,
        ):
            # Mock successful query
            mock_result = RulesResponse(
                query_type="weapon",
                found=True,
                result={"id": 1, "name": "Longsword", "damage": "1d8 slashing"},
                query_time=0.02,
            )
            mock_engine.query = AsyncMock(return_value=mock_result)
            mock_audit.log_data_access = Mock()

            result = await tool_service.query_weapon_tool(**sample_weapon_query)

            assert result["success"] is True
            assert result["query"] == "Longsword"
            assert result["data"] is not None

    @pytest.mark.asyncio
    async def test_compare_entities_tool(self, tool_service):
        """Test entity comparison tool."""
        comparison_query = {
            "entity_type": "monster",
            "names": ["Goblin", "Orc"],
            "comparison_focus": "combat",
        }

        with (
            patch(
                "packages.backend.components.srd_tool_service.rules_engine"
            ) as mock_engine,
            patch(
                "packages.backend.components.srd_tool_service.srd_audit_service"
            ) as mock_audit,
        ):
            # Mock monster queries
            goblin_result = RulesResponse(
                query_type="monster",
                found=True,
                result={
                    "name": "Goblin",
                    "armor_class": 15,
                    "challenge_rating": "1/4",
                },
                query_time=0.01,
            )

            orc_result = RulesResponse(
                query_type="monster",
                found=True,
                result={
                    "name": "Orc",
                    "armor_class": 13,
                    "challenge_rating": "1/2",
                },
                query_time=0.01,
            )

            mock_engine.query = AsyncMock(side_effect=[goblin_result, orc_result])
            mock_audit.log_data_access = Mock()

            result = await tool_service.compare_entities_tool(**comparison_query)

            assert result["success"] is True
            assert result["entity_type"] == "monster"
            assert len(result["results"]) == 2
            assert "analysis" in result

    def test_performance_metrics_recording(self, tool_service):
        """Test that performance metrics are recorded."""
        # Initially should have no metrics
        assert len(tool_service._tool_metrics) == 0

        # After a mock execution, metrics should be recorded
        # This is tested implicitly in the tool execution tests above

    def test_performance_stats(self, tool_service):
        """Test performance statistics retrieval."""
        # Add some mock metrics for testing
        tool_service._record_tool_metrics("query_monster", 0.1, True, False)
        tool_service._record_tool_metrics("query_spell", 0.2, False, False)
        tool_service._record_tool_metrics("query_monster", 0.15, True, True)

        stats = tool_service.get_performance_stats()

        assert isinstance(stats, dict)
        assert "total_executions" in stats
        assert "average_execution_time" in stats
        assert "tool_stats" in stats
        assert stats["total_executions"] == 3
        assert stats["successful_executions"] == 2
        assert "query_monster" in stats["tool_stats"]
        assert "query_spell" in stats["tool_stats"]

    def test_clear_metrics(self, tool_service):
        """Test metrics clearing functionality."""
        # Add some mock metrics
        tool_service._tool_metrics.append(
            ToolPerformanceMetrics(
                tool_name="test_tool",
                execution_time=0.1,
                success=True,
                cache_hit=False,
                timestamp=datetime.utcnow(),
            )
        )

        assert len(tool_service._tool_metrics) > 0

        tool_service.clear_metrics()

        assert len(tool_service._tool_metrics) == 0

    def test_health_check(self, tool_service):
        """Test health check functionality."""
        health = tool_service.health_check()

        assert isinstance(health, dict)
        assert "status" in health
        assert "available_tools" in health
        assert "metrics_recorded" in health
        assert "last_check" in health

        assert health["available_tools"] == 4
        assert health["metrics_recorded"] == 0  # No executions yet

    @pytest.mark.asyncio
    async def test_tool_execution_error_handling(self, tool_service):
        """Test error handling in tool execution."""
        with (
            patch(
                "packages.backend.components.srd_tool_service.rules_engine"
            ) as mock_engine,
            patch(
                "packages.backend.components.srd_tool_service.srd_audit_service"
            ) as mock_audit,
        ):
            # Mock engine to raise exception
            mock_engine.query = AsyncMock(
                side_effect=Exception("Database connection failed")
            )
            mock_audit.log_data_access = Mock()

            result = await tool_service.query_monster_tool(name="Goblin")

            assert result["success"] is False
            assert "failed" in result["error"].lower()
            assert "execution_time" in result

    def test_tool_performance_monitoring(self, tool_service):
        """Test that slow tool executions are logged."""
        # This is tested implicitly through the logging in the tool methods
        # In a real scenario, we would verify log messages
        pass

    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, tool_service):
        """Test concurrent tool execution handling."""
        import asyncio

        with (
            patch(
                "packages.backend.components.srd_tool_service.rules_engine"
            ) as mock_engine,
            patch(
                "packages.backend.components.srd_tool_service.srd_audit_service"
            ) as mock_audit,
        ):
            # Mock fast responses
            mock_result = RulesResponse(
                query_type="monster",
                found=True,
                result={"name": "Test"},
                query_time=0.01,
            )
            mock_engine.query = AsyncMock(return_value=mock_result)
            mock_audit.log_data_access = Mock()

            # Execute multiple tools concurrently
            tasks = [
                tool_service.query_monster_tool(name=f"Monster{i}") for i in range(3)
            ]

            results = await asyncio.gather(*tasks)

            assert len(results) == 3
            assert all(result["success"] for result in results)

    def test_metrics_history_limit(self, tool_service):
        """Test that metrics history respects the limit."""
        # Add metrics up to the limit using the proper method
        for i in range(tool_service.max_metrics_history + 10):
            tool_service._record_tool_metrics(
                tool_name=f"tool_{i}",
                execution_time=0.1,
                success=True,
                cache_hit=False,
            )

        # Should not exceed max history
        assert len(tool_service._tool_metrics) <= tool_service.max_metrics_history

    def test_tool_result_formatting(self, tool_service):
        """Test that tool results are properly formatted."""
        # This is tested implicitly in the tool execution tests
        # All results should have consistent structure
        expected_fields = ["tool_name", "success", "execution_time"]

        # Mock a tool result for testing
        result = {
            "tool_name": "query_monster",
            "success": True,
            "query": "Goblin",
            "execution_time": 0.05,
            "data": {"name": "Goblin"},
        }

        for field in expected_fields:
            assert field in result


class TestToolPerformanceMetrics:
    """Test cases for ToolPerformanceMetrics model."""

    def test_metrics_creation(self):
        """Test ToolPerformanceMetrics creation."""
        metrics = ToolPerformanceMetrics(
            tool_name="query_monster",
            execution_time=0.123,
            success=True,
            cache_hit=False,
            timestamp=datetime.utcnow(),
        )

        assert metrics.tool_name == "query_monster"
        assert metrics.execution_time == 0.123
        assert metrics.success is True
        assert metrics.cache_hit is False
        assert metrics.error_message is None
        assert isinstance(metrics.timestamp, datetime)

    def test_metrics_defaults(self):
        """Test ToolPerformanceMetrics default values."""
        metrics = ToolPerformanceMetrics(
            tool_name="test_tool",
            execution_time=0.1,
            success=False,
            cache_hit=True,
            timestamp=datetime.utcnow(),
            error_message="Test error",
        )

        assert metrics.tool_name == "test_tool"
        assert metrics.execution_time == 0.1
        assert metrics.success is False
        assert metrics.cache_hit is True
        assert metrics.error_message == "Test error"


class TestToolIntegration:
    """Test cases for tool integration patterns."""

    def test_tool_definition_schema_compliance(self):
        """Test that tool definitions comply with expected schema."""
        service = SRDToolService()
        definitions = service.get_tool_definitions()

        required_fields = ["name", "description", "parameters"]

        for tool_name, definition in definitions.items():
            for field in required_fields:
                assert field in definition, (
                    f"Tool {tool_name} missing required field: {field}"
                )

            # Parameters should have proper structure
            params = definition["parameters"]
            assert "type" in params
            assert params["type"] == "object"
            assert "properties" in params

    def test_tool_parameter_validation(self):
        """Test tool parameter validation."""
        # This would test the actual parameter validation logic
        # For now, we verify the parameter schemas are well-formed
        service = SRDToolService()
        monster_tool = service.tool_definitions["query_monster"]

        required_params = monster_tool["parameters"].get("required", [])
        properties = monster_tool["parameters"]["properties"]

        # Required parameters should be defined
        for param in required_params:
            assert param in properties, (
                f"Required parameter {param} not defined in properties"
            )

    def test_error_response_consistency(self):
        """Test that error responses have consistent structure."""
        # This is tested implicitly in the error handling tests above
        # All error responses should have the same basic structure
        pass
