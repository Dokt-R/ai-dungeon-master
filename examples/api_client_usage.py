"""
Example usage of the thin API client.
Demonstrates proper usage patterns and error handling.
"""

import asyncio
import os

from packages.shared.api_client import ApiClient
from packages.shared.exceptions import (
    AIAPIError,
    CustomException,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from packages.shared.models import (
    AddCharacterRequest,
    ListCharactersRequest,
    RemoveCharacterRequest,
    ServerConfigModel,
    UpdateCharacterRequest,
)


async def example_character_operations():
    """Example of character CRUD operations using the thin API client."""

    # Use async context manager for automatic cleanup
    async with ApiClient(base_url="http://localhost:8000") as client:
        player_id = "example_player_123"

        try:
            # Add a new character
            print("Adding a new character...")
            add_request = AddCharacterRequest(
                player_id=player_id,
                name="Aragorn",
                character_url="https://ddb.ac/characters/12345",
            )
            character_data = await client.add_character(add_request)
            character_id = character_data["character_id"]
            print(f"Character added successfully: {character_data}")

            # List all characters for the player
            print("\nListing all characters...")
            list_request = ListCharactersRequest(player_id=player_id)
            characters_data = await client.list_characters(list_request)
            print(f"Characters: {characters_data}")

            # Update the character
            print("\nUpdating character...")
            update_request = UpdateCharacterRequest(
                character_id=character_id,
                name="Aragorn, King of Gondor",
                character_url="https://ddb.ac/characters/12345-updated",
            )
            updated_data = await client.update_character(update_request)
            print(f"Character updated: {updated_data}")

            # Get character info
            print("\nGetting character info...")
            character_info = await client.get_character_info(str(character_id))
            print(f"Character info: {character_info}")

            # Remove the character
            print("\nRemoving character...")
            remove_request = RemoveCharacterRequest(character_id=character_id)
            await client.remove_character(remove_request)
            print("Character removed successfully")

        except ValidationError as e:
            print(f"Validation error: {e.message}")
            print(f"Error code: {e.error_code}")
            print(f"Details: {e.details}")
        except NotFoundError as e:
            print(f"Resource not found: {e.message}")
        except PermissionDeniedError as e:
            print(f"Permission denied: {e.message}")
        except AIAPIError as e:
            print(f"AI API error: {e.message}")
        except CustomException as e:
            print(f"API error: {e.message}")
            print(f"Error code: {e.error_code}")
            print(f"Status code: {e.status_code}")


async def example_campaign_operations():
    """Example of campaign operations using the thin API client."""

    async with ApiClient(base_url="http://localhost:8000") as client:
        server_id = "example_server_456"
        campaign_name = "The Fellowship of the Ring"
        player_id = "example_player_123"

        try:
            # Create a new campaign
            print("Creating a new campaign...")
            campaign_data = await client.create_campaign(
                {
                    "server_id": server_id,
                    "campaign_name": campaign_name,
                    "owner_id": player_id,
                }
            )
            print(f"Campaign created: {campaign_data}")

            # Get campaign details
            print("\nGetting campaign details...")
            details = await client.get_campaign_details(server_id, campaign_name)
            print(f"Campaign details: {details}")

            # Join the campaign
            print("\nJoining campaign...")
            await client.join_campaign(
                {
                    "server_id": server_id,
                    "campaign_name": campaign_name,
                    "player_id": player_id,
                }
            )
            print("Joined campaign successfully")

            # Get campaign players
            print("\nGetting campaign players...")
            campaign_id = details["campaign_id"]
            players = await client.get_campaign_players(campaign_id)
            print(f"Campaign players: {players}")

            # End campaign session
            print("\nEnding campaign session...")
            await client.end_campaign(
                {
                    "server_id": server_id,
                    "player_id": player_id,
                }
            )
            print("Campaign session ended")

            # Delete the campaign
            print("\nDeleting campaign...")
            await client.delete_campaign(
                {
                    "server_id": server_id,
                    "campaign_name": campaign_name,
                    "requester_id": player_id,
                    "is_admin": True,
                }
            )
            print("Campaign deleted successfully")

        except CustomException as e:
            print(f"Campaign operation error: {e.message}")
            print(f"Error code: {e.error_code}")


async def example_server_config():
    """Example of server configuration using the thin API client."""

    async with ApiClient(base_url="http://localhost:8000") as client:
        server_id = "example_server_456"

        try:
            # Set server configuration
            print("Setting server configuration...")
            config = ServerConfigModel(
                api_key="sk-example-api-key-12345",
                dm_roll_visibility="hidden",
                player_roll_mode="digital",
                character_sheet_mode="digital_sheet",
            )
            result = await client.set_server_config(server_id, config)
            print(f"Server config updated: {result}")

        except ValidationError as e:
            print(f"Configuration validation error: {e.message}")
        except CustomException as e:
            print(f"Server config error: {e.message}")


async def example_error_handling():
    """Example of comprehensive error handling patterns."""

    async with ApiClient(base_url="http://localhost:8000") as client:
        try:
            # Try to get a non-existent character
            await client.get_character_info("999999")

        except NotFoundError as e:
            print(f"Expected not found error: {e.message}")
            print(f"Player-facing message: {e.player_message}")

        except ValidationError as e:
            print(f"Validation error: {e.message}")
            print(f"Error details: {e.details}")

        except PermissionDeniedError as e:
            print(f"Permission denied: {e.message}")

        except AIAPIError as e:
            print(f"AI service error: {e.message}")

        except CustomException as e:
            # Catch-all for any other API errors
            print(f"General API error: {e.message}")
            print(f"Error code: {e.error_code}")
            print(f"HTTP status: {e.status_code}")
            print(f"Details: {e.details}")

        except Exception as e:
            # Catch any unexpected errors
            print(f"Unexpected error: {e}")


async def example_with_manual_client_management():
    """Example showing manual client lifecycle management."""

    # Create client manually
    client = ApiClient(
        base_url="http://localhost:8000",
        timeout=30.0,  # Custom timeout
    )

    try:
        # Use the client
        player_status = await client.get_player_status("example_player_123")
        print(f"Player status: {player_status}")

    except CustomException as e:
        print(f"Error: {e.message}")

    finally:
        # Always close the client to free resources
        await client.close()


async def main():
    """Run all examples."""
    print("=== Character Operations Example ===")
    await example_character_operations()

    print("\n=== Campaign Operations Example ===")
    await example_campaign_operations()

    print("\n=== Server Configuration Example ===")
    await example_server_config()

    print("\n=== Error Handling Example ===")
    await example_error_handling()

    print("\n=== Manual Client Management Example ===")
    await example_with_manual_client_management()


if __name__ == "__main__":
    # Set environment variable for API base URL if needed
    os.environ.setdefault("FAST_API", "http://localhost:8000")

    # Run the examples
    asyncio.run(main())
