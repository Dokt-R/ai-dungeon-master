#!/usr/bin/env python3
"""
Simple test script for the utility LLM endpoint.
"""

import asyncio
import os
from packages.shared.api_client import ApiClient

async def test_utility_llm():
    """Test the utility LLM endpoint."""
    
    # Create API client
    api_client = ApiClient(base_url="http://localhost:8000")
    
    try:
        print("Testing utility LLM endpoint...")
        
        # Test with a simple prompt
        test_prompt = "Hello! Please respond with a short greeting."
        
        print(f"Sending prompt: {test_prompt}")
        
        response = await api_client.test_llm(test_prompt)
        
        print("Response received:")
        print(f"Status: {response.get('status')}")
        print(f"Response: {response.get('response')}")
        print(f"Metadata: {response.get('metadata')}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await api_client.close()

if __name__ == "__main__":
    asyncio.run(test_utility_llm())