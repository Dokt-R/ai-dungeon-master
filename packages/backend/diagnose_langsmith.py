"""
LangSmith Integration Diagnostic Tool

This script diagnoses issues with LangSmith observability integration,
helping identify why traces might not be appearing in the dashboard.

Run this script to diagnose LangSmith integration issues.
"""

import os
import sys
import asyncio
import time
import json
from typing import Dict, Any

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from packages.backend.components.observability_service import observability_service
from packages.shared.logging_config import get_logger

logger = get_logger(__name__)


class LangSmithDiagnostic:
    """Comprehensive LangSmith integration diagnostic tool."""

    def __init__(self):
        self.diagnostic_results = {}

    async def run_full_diagnostic(self) -> Dict[str, Any]:
        """Run complete LangSmith integration diagnostic."""
        print("🔍 LangSmith Integration Diagnostic Tool")
        print("=" * 50)

        # 1. Check environment variables
        print("\n1. Environment Variable Check")
        print("-" * 30)
        env_status = await self.check_environment_variables()
        self.diagnostic_results["environment"] = env_status

        # 2. Check service initialization
        print("\n2. Service Initialization Check")
        print("-" * 35)
        init_status = await self.check_service_initialization()
        self.diagnostic_results["initialization"] = init_status

        # 3. Test basic trace operations
        print("\n3. Basic Trace Operations Test")
        print("-" * 32)
        trace_status = await self.test_trace_operations()
        self.diagnostic_results["trace_test"] = trace_status

        # 4. Test AI workflow traces
        print("\n4. AI Workflow Trace Test")
        print("-" * 27)
        workflow_status = await self.test_workflow_traces()
        self.diagnostic_results["workflow_test"] = workflow_status

        # 5. Service health check
        print("\n5. Service Health Check")
        print("-" * 23)
        health_status = self.check_service_health()
        self.diagnostic_results["health"] = health_status

        # 6. Summary and recommendations
        self.print_diagnostic_summary()
        self.print_recommendations()

        return self.diagnostic_results

    async def check_environment_variables(self) -> Dict[str, Any]:
        """Check required LangSmith environment variables."""
        status = {
            "lan_api_key": False,
            "lan_project": False,
            "lan_endpoint": None,
            "lan_tracing": None,
            "issues": []
        }

        # Check API Key
        api_key = os.getenv("LANGSMITH_API_KEY")
        if api_key:
            status["lan_api_key"] = len(api_key) > 20  # Basic format check
            print(f"✅ LANGSMITH_API_KEY set: {api_key[:10]}..." if status["lan_api_key"] else f"❌ LANGSMITH_API_KEY invalid")
        else:
            status["issues"].append("LANGSMITH_API_KEY not set")
            print("❌ LANGSMITH_API_KEY not set")

        # Check Project
        project = os.getenv("LANGSMITH_PROJECT", "ai-dungeon-master")
        status["lan_project"] = bool(project)
        print(f"✅ LANGSMITH_PROJECT: {project}" if status["lan_project"] else "❌ LANGSMITH_PROJECT not set")

        # Check Endpoint
        endpoint = os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")
        status["lan_endpoint"] = endpoint
        print(f"✅ LANGSMITH_ENDPOINT: {endpoint}")

        # Check Tracing Enabled
        tracing = os.getenv("LANGSMITH_TRACING", "false").lower()
        status["lan_tracing"] = tracing
        if tracing == "true":
            print("✅ LANGSMITH_TRACING: enabled")
        else:
            status["issues"].append("LANGSMITH_TRACING not set to 'true' (currently disabled)")
            print("❌ LANGSMITH_TRACING: disabled (set to 'true' to enable)")

        return status

    async def check_service_initialization(self) -> Dict[str, Any]:
        """Check if observability service initializes correctly."""
        status = {
            "initialization_attempted": False,
            "initialization_success": False,
            "langgraph_available": False,
            "errors": []
        }

        try:
            # Try to initialize the service
            status["initialization_attempted"] = True
            success = await observability_service.initialize()

            if success:
                status["initialization_success"] = True
                print("✅ Observability service initialized successfully")
            else:
                status["errors"].append("Observability service initialization failed")
                print("❌ Observability service initialization failed")

        except Exception as e:
            status["errors"].append(f"Initialization error: {str(e)}")
            print(f"❌ Initialization error: {str(e)}")

        return status

    async def test_trace_operations(self) -> Dict[str, Any]:
        """Test basic trace operations."""
        status = {
            "basic_trace_tested": False,
            "basic_trace_success": False,
            "ai_operation_tested": False,
            "ai_operation_success": False,
            "errors": []
        }

        try:
            # Test basic trace operation
            status["basic_trace_tested"] = True
            test_operation = "langsmith_diagnostic_test_operation"
            start_time = time.time()

            with observability_service.trace_operation(test_operation, diagnostic_mode=True) as trace_id:
                time.sleep(0.1)  # Simulate some work
                execution_time = time.time() - start_time
                print(".4f"                status["basic_trace_success"] = bool(trace_id)
                if trace_id:
                    print(f"✅ Trace ID generated: {trace_id}")
                else:
                    print("❌ No trace ID returned")

        except Exception as e:
            status["errors"].append(f"Basic trace error: {str(e)}")
            print(f"❌ Basic trace test failed: {str(e)}")

        return status

    async def test_workflow_traces(self) -> Dict[str, Any]:
        """Test AI workflow tracing."""
        status = {
            "workflow_trace_tested": False,
            "workflow_trace_success": False,
            "errors": []
        }

        try:
            status["workflow_trace_tested"] = True

            # Test AI workflow decorator
            @observability_service.trace_ai_workflow_decorator(
                workflow_name="diagnostic_workflow",
                workflow_type="diagnostic_test"
            )
            async def test_ai_workflow():
                await asyncio.sleep(0.05)  # Simulate AI processing
                return {"test": "completed", "timestamp": time.time()}

            result = await test_ai_workflow()

            if result and result.get("test") == "completed":
                status["workflow_trace_success"] = True
                print("✅ AI workflow trace test successful")
            else:
                status["errors"].append("AI workflow returned unexpected result")
                print("❌ AI workflow returned unexpected result")

        except Exception as e:
            status["errors"].append(f"AI workflow error: {str(e)}")
            print(f"❌ AI workflow test failed: {str(e)}")

        return status

    def check_service_health(self) -> Dict[str, Any]:
        """Get detailed service health information."""
        health = {
            "service_initialized": False,
            "config_details": {},
            "circut_breaker_state": "unknown"
        }

        try:
            health_status = observability_service.get_health_status()

            if health_status:
                print("📊 Observability Service Health:")
                for key, value in health_status.items():
                    print(f"   {key}: {value}")
                health["service_initialized"] = True
                health["config_details"] = health_status

            # Check circuit breaker
            if hasattr(observability_service, 'is_circuit_breaker_open'):
                circuit_open = observability_service.is_circuit_breaker_open()
                health["circuit_breaker_open"] = circuit_open
                print(f"   Circuit Breaker: {'OPEN' if circuit_open else 'CLOSED'}")

        except Exception as e:
            print(f"❌ Health check failed: airports{e}")
            health["errors"] = [str(e)]

        return health

    def print_diagnostic_summary(self):
        """Print comprehensive diagnostic summary."""
        print("\n" + "=" * 50)
        print("🔍 DIAGNOSTIC SUMMARY")
        print("=" * 50)

        all_good = True
        critical_issues = []

        # Check environment
        env_issues = self.diagnostic_results.get("environment", {}).get("issues", [])
        if env_issues:
            all_good = False
            critical_issues.extend(env_issues)
            print("❌ Environment Issues:")
            for issue in env_issues:
                print("5s")

        # Check initialization
        init_issues = self.diagnostic_results.get("initialization", {}).get("errors", [])
        if init_issues:
            all_good = False
            critical_issues.extend(init_issues)
            print("❌ Initialization Issues:")
            for issue in init_issues:
                print(f"   • {issue}")

        # Check trace tests
        trace_issues = self.diagnostic_results.get("trace_test", {}).get("errors", [])
        if trace_issues:
            all_good = False
            critical_issues.extend(trace_issues)
            print("❌ Trace Issues:")
            for issue in trace_issues:
                print("5s")

        if all_good:
            print("✅ All diagnostic checks passed!")
            print("🔍 LangSmith integration appears to be configured correctly")
        else:
            print("❌ Issues found that may prevent LangSmith traces from appearing")
            print("\n🔧 Critical Issues:")
            for issue in critical_issues:
                print(f"   • {issue}")

    def print_recommendations(self):
        """Print troubleshooting recommendations."""
        print("\n" + "=" * 50)
        print("🛠️  TROUBLESHOOTING RECOMMENDATIONS")
        print("=" * 50)

        print("\n1. Environment Setup:")
        print("   export LANGSMITH_API_KEY='ls__your_api_key_here'")
        print("   export LANGSMITH_PROJECT='ai-dungeon-master'")
        print("   export LANGSMITH_TRACING='true'")
        print("   export LANGSMITH_ENDPOINT='https://api.smith.langchain.com'")

        print("\n2. Verify API Key:")
        print("   • Get key from https://smith.langchain.com/ (Settings > API Keys)")
        print("   • Key should start with 'ls__' or 'lsv2_'")
        print("   • Test with curl: curl -H 'x-api-key: YOUR_KEY' https://api.smith.langchain.com/api/v1/runs")

        print("\n3. Enable Tracing:")
        print("   • Ensure LANGSMITH_TRACING='true' (not 'false' or unset)")
        print("   • Restart your application after changing env vars")

        print("\n4. Check Network Connectivity:")
        print("   • Verify internet connection to api.smith.langchain.com")
        print("   • Check firewall/proxy settings")

        print("\n5. Test Manually:")
        print("   • Run this diagnostic script: python packages/backend/diagnose_langsmith.py")
        print("   • Check for any error messages or warnings")

        print("\n6. LangSmith Dashboard:")
        print("   • Go to https://smith.langchain.com/")
        print("   • Select the correct project in the dropdown")
        print("   • Look for traces in 'Runs' section")

        print("\n📞 For help: Check observability_service_usage_guide.md in docs/")


async def main():
    """Main diagnostic function."""
    diagnostic = LangSmithDiagnostic()
    results = await diagnostic.run_full_diagnostic()

    print("\n" + "=" * 50)
    print("📋 COMPLETE DIAGNOSTIC RESULTS")
    print("=" * 50)

    # Save detailed results
    try:
        with open("langsmith_diagnostic_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print("💾 Detailed results saved to: langsmith_diagnostic_results.json")
    except Exception as e:
        print(f"❌ Could not save results: {e}")

    return results


if __name__ == "__main__":
    print("🔍 Starting LangSmith Integration Diagnostic...")
    asyncio.run(main())