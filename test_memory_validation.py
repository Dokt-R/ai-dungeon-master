#!/usr/bin/env python3
"""
Simple test runner for memory validation tests.
"""
import subprocess
import sys

def run_test():
    """Run the memory validation tests."""
    try:
        # Run pytest on the specific test file
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "tests/unit/shared/test_memory_validation.py",
            "-v",
            "--tb=short"
        ], capture_output=True, text=True, cwd="/workspaces/ai-dungeon-master")

        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print(f"\nReturn code: {result.returncode}")

        return result.returncode == 0

    except Exception as e:
        print(f"Error running tests: {e}")
        return False

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)