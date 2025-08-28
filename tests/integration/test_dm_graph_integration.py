#!/usr/bin/env python3
"""
Test script to verify DM Graph integration with the action API.
This script tests the end-to-end integration of the DM Graph service.
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest

# Add the packages directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from packages.backend.ai.dm_graph import dm_graph_service
from packages.backend.components.ai_client import ai_client
from packages.shared.models import ActionRequest

pytestmark = pytest.mark.asyncio

async def test_dm_graph_integration():
    """Test the DM Graph integration with a simple action request."""
    print("Testing DM Graph integration...")
    
    # Initialize AI client first (required for DM Graph)
    print("Initializing AI client...")
    try:
        # Set up test environment variables
        os.environ["AI_PROVIDER_API_KEY"] = os.getenv("AI_PROVIDER_API_KEY", "test-key")
        os.environ["AI_PROVIDER"] = "openai"
        os.environ["AI_PROVIDER_MODEL"] = "gpt-3.5-turbo"
        
        ai_initialized = await ai_client.initialize()
        if not ai_initialized:
            print("AI client initialization failed")
            return False
        print("AI client initialized successfully")
    except Exception as e:
        print(f"AI client initialization error: {e}")
        return False
    
    # Initialize DM Graph service
    print("Initializing DM Graph service...")
    try:
        dm_initialized = await dm_graph_service.initialize()
        if not dm_initialized:
            print("DM Graph service initialization failed")
            return False
        print("DM Graph service initialized successfully")
    except Exception as e:
        print(f"DM Graph service initialization error: {e}")
        return False
    
    # Test a simple interaction
    print("Testing DM Graph interaction...")
    try:
        result = await dm_graph_service.process_interaction(
            user_prompt="Hello, I want to explore the forest",
            session_id="test-session-123",
            correlation_id="test-correlation-456"
        )
        
        print(f"DM Graph response: {result['narrative']}")
        print(f"Session ID: {result['session_id']}")
        print(f"Execution time: {result['execution_time']:.2f}s")
        
        if result.get("error"):
            print(f"Error occurred: {result['error']}")
            return False
            
        print("DM Graph integration test passed!")
        return True
        
    except Exception as e:
        print(f"DM Graph interaction error: {e}")
        return False


async def test_action_request_model():
    """Test the ActionRequest model validation."""
    print("\nTesting ActionRequest model...")
    
    try:
        # Test valid request
        valid_request = ActionRequest(
            prompt="I want to attack the goblin",
            session_id="test-session-123",
            user_id="test-user-456"
        )
        print("ActionRequest model validation passed")
        return True
        
    except Exception as e:
        print(f"ActionRequest model validation failed: {e}")
        return False


async def main():
    """Run all integration tests."""
    print("=" * 50)
    print("DM Graph Integration Test")
    print("=" * 50)
    
    success = True
    
    # Test ActionRequest model
    success &= await test_action_request_model()
    
    # Test DM Graph integration
    success &= await test_dm_graph_integration()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All integration tests passed!")
        print("The DM Graph is successfully integrated with the system.")
    else:
        print("❌ Some integration tests failed!")
        print("Check the error messages above for details.")
    
    print("=" * 50)
    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)