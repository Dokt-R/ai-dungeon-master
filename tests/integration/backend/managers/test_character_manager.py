import pytest

from packages.shared.exceptions import NotFoundError, ValidationError
from packages.shared.models import CampaignPlayerLink

pytestmark = pytest.mark.asyncio


class TestAddCharacter:
    async def test_add_character_normal(
        self, managers, session, insert_player, select_character
    ):
        await insert_player()
        character = await managers.character.add_character(
            "user-id-1", "Hero", "http://dndbeyond.com/hero"
        )
        assert isinstance(character.character_id, int)
        db_char = await select_character(character.character_id)
        assert db_char.name == "Hero"
        assert db_char.character_url == "http://dndbeyond.com/hero"

    async def test_add_character_missing_player(self, managers):
        with pytest.raises(NotFoundError):
            await managers.character.add_character("user-id-2", "Hero")

    async def test_add_character_duplicate_name(self, managers, session, insert_player):
        await insert_player()
        await managers.character.add_character("user-id-1", "Hero")
        with pytest.raises(ValidationError):
            await managers.character.add_character("user-id-1", "Hero")

    async def test_add_character_without_character_url(
        self, managers, session, insert_player, select_character
    ):
        await insert_player()
        character = await managers.character.add_character("user-id-1", "Hero")
        assert isinstance(character.character_id, int)
        db_char = await select_character(character.character_id)
        assert db_char.name == "Hero"
        assert db_char.character_url is None


class TestUpdateCharacter:
    async def test_update_character_normal(
        self, managers, session, insert_player, select_character
    ):
        await insert_player()
        character = await managers.character.add_character("user-id-1", "Hero", "url1")
        result = await managers.character.update_character(
            character.character_id, name="Hero2", character_url="url2"
        )
        assert result.name == "Hero2"
        db_char = await select_character(character.character_id)
        assert db_char.name == "Hero2"
        assert db_char.character_url == "url2"

    async def test_update_character_no_fields(self, managers, session, insert_player):
        await insert_player()
        character = await managers.character.add_character("user-id-1", "Hero")
        with pytest.raises(ValidationError):
            await managers.character.update_character(character.character_id)

    async def test_update_character_not_found(self, managers):
        with pytest.raises(NotFoundError):
            await managers.character.update_character(9999, name="NewName")

    async def test_update_character_duplicate_name(
        self, managers, session, insert_player
    ):
        await insert_player()
        await managers.character.add_character("user-id-1", "Hero")
        char2 = await managers.character.add_character("user-id-1", "Hero2")
        with pytest.raises(ValidationError):
            await managers.character.update_character(char2.character_id, name="Hero")


class TestRemoveCharacter:
    async def test_remove_character_normal(
        self, managers, session, insert_player, select_character
    ):
        await insert_player()
        character = await managers.character.add_character("user-id-1", "Hero")
        result = await managers.character.remove_character(character.character_id)
        assert result is True
        db_char = await select_character(character.character_id)
        assert db_char is None

    async def test_remove_character_not_found(self, managers):
        with pytest.raises(NotFoundError):
            result = await managers.character.remove_character(9999)
            assert result is False

    async def test_remove_character_does_not_set_campaignplayers_null(
        self, managers, session, insert_player
    ):
        player = await insert_player()
        player_id = player.player_id

        character = await managers.character.add_character("user-id-1", "Hero")
        character_id = character.character_id

        campaign = await managers.campaign.create_campaign(
            "server_id", "campaign_name", "owner_id"
        )
        campaign_id = campaign.campaign_id

        session.add(campaign)
        await session.commit()

        link = CampaignPlayerLink(
            campaign_id=campaign_id,
            player_id=player_id,
            character_id=character_id,
        )
        session.add(link)
        await session.commit()

        await managers.character.remove_character(character_id)

        db_link = await session.get(CampaignPlayerLink, (campaign_id, player_id))
        assert db_link is not None


class TestGetCharactersForPlayer:
    async def test_get_characters_for_player_normal(
        self, managers, session, insert_player
    ):
        await insert_player()
        await managers.character.add_character("user-id-1", "Hero", "url1")
        await managers.character.add_character("user-id-1", "Hero2", "url2")
        chars = await managers.character.get_characters_for_player("user-id-1")
        assert isinstance(chars, list)
        assert len(chars) == 2
        names = {c.name for c in chars}
        assert "Hero" in names and "Hero2" in names

    async def test_get_characters_for_player_no_characters(
        self, managers, session, insert_player
    ):
        await insert_player()
        chars = await managers.character.get_characters_for_player("user-id-1")
        assert chars == []

    async def test_get_characters_for_player_nonexistent_player(self, managers):
        chars = await managers.character.get_characters_for_player("nonexistent")
        assert chars == []
