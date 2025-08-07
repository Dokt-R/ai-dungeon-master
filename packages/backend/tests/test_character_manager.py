import pytest
from packages.shared.error_handler import ValidationError, NotFoundError
from packages.shared.models import Campaign, CampaignPlayerLink, Character


class TestAddCharacter:
    def test_add_character_normal(
        self, managers, session, insert_player, select_character
    ):
        insert_player()
        character = managers.character.add_character(
            "user-id-1", "Hero", "http://dndbeyond.com/hero"
        )
        assert isinstance(character.character_id, int)
        db_char = select_character(character.character_id)
        assert db_char.name == "Hero"
        assert db_char.character_url == "http://dndbeyond.com/hero"

    def test_add_character_missing_player(self, managers):
        with pytest.raises(NotFoundError):
            managers.character.add_character("user-id-2", "Hero")

    def test_add_character_duplicate_name(self, managers, session, insert_player):
        insert_player()
        managers.character.add_character("user-id-1", "Hero")
        with pytest.raises(ValidationError):
            managers.character.add_character("user-id-1", "Hero")

    def test_add_character_without_character_url(
        self, managers, session, insert_player, select_character
    ):
        insert_player()
        character = managers.character.add_character("user-id-1", "Hero")
        assert isinstance(character.character_id, int)
        db_char = select_character(character.character_id)
        assert db_char.name == "Hero"
        assert db_char.character_url is None


class TestUpdateCharacter:
    def test_update_character_normal(
        self, managers, session, insert_player, select_character
    ):
        insert_player()
        character = managers.character.add_character("user-id-1", "Hero", "url1")
        result = managers.character.update_character(
            character.character_id, name="Hero2", character_url="url2"
        )
        assert result.name == "Hero2"
        db_char = select_character(character.character_id)
        assert db_char.name == "Hero2"
        assert db_char.character_url == "url2"

    def test_update_character_no_fields(self, managers, session, insert_player):
        insert_player()
        character = managers.character.add_character("user-id-1", "Hero")
        with pytest.raises(ValidationError):
            managers.character.update_character(character.character_id)

    def test_update_character_not_found(self, managers):
        with pytest.raises(NotFoundError):
            managers.character.update_character(9999, name="NewName")

    def test_update_character_duplicate_name(self, managers, session, insert_player):
        insert_player()
        managers.character.add_character("user-id-1", "Hero")
        char2 = managers.character.add_character("user-id-1", "Hero2")
        with pytest.raises(ValidationError):
            managers.character.update_character(char2.character_id, name="Hero")


class TestRemoveCharacter:
    def test_remove_character_normal(
        self, managers, session, insert_player, select_character
    ):
        insert_player()
        character = managers.character.add_character("user-id-1", "Hero")
        result = managers.character.remove_character(character.character_id)
        assert result is True
        db_char = select_character(character.character_id)
        assert db_char is None

    def test_remove_character_not_found(self, managers):
        result = managers.character.remove_character(9999)
        assert result is False

    def test_remove_character_does_not_set_campaignplayers_null(
        self, managers, session, insert_player
    ):
        player = insert_player()
        character = managers.character.add_character("user-id-1", "Hero")
        campaign = Campaign(server_id="server1", campaign_name="Epic Quest", owner_id="owner1")
        session.add(campaign)
        session.commit()
        
        link = CampaignPlayerLink(campaign_id=campaign.campaign_id, player_id=player.user_id, character_id=character.character_id)
        session.add(link)
        session.commit()

        managers.character.remove_character(character.character_id)

        db_link = session.get(CampaignPlayerLink, (campaign.campaign_id, player.user_id))
        assert db_link is not None


class TestGetCharactersForPlayer:
    def test_get_characters_for_player_normal(
        self, managers, session, insert_player
    ):
        insert_player()
        managers.character.add_character("user-id-1", "Hero", "url1")
        managers.character.add_character("user-id-1", "Hero2", "url2")
        chars = managers.character.get_characters_for_player("user-id-1")
        assert isinstance(chars, list)
        assert len(chars) == 2
        names = {c.name for c in chars}
        assert "Hero" in names and "Hero2" in names

    def test_get_characters_for_player_no_characters(
        self, managers, session, insert_player
    ):
        insert_player()
        chars = managers.character.get_characters_for_player("user-id-1")
        assert chars == []

    def test_get_characters_for_player_nonexistent_player(self, managers):
        chars = managers.character.get_characters_for_player("nonexistent")
        assert chars == []
