import asyncio
import os
import sys

# Add the packages directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "packages"))

from packages.backend.scripts.srd_loaders import load_srd_data
from packages.shared.db import get_async_session


async def test_load():
    try:
        async with get_async_session() as session:
            load_srd_data(session, "srd/json_files")
            print("SRD data loaded successfully!")
    except Exception as e:
        print(f"Error loading SRD data: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_load())
