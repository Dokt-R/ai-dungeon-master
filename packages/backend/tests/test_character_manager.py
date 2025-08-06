import pytest
from packages.shared.error_handler import ValidationError, NotFoundError


class TestAddCharacter:
    def test_add_character_normal(
        self, managers, conn, insert_player, select_character
    ):
        insert_player()
        char_id = managers.character.add_character(
            "user-id-1", "Hero", "http://dndbeyond.com/hero"
        )
        assert isinstance(char_id, int)
        row = select_character(char_id)
        assert row["name"] == "Hero"
        assert row["dnd_beyond_url"] == "http://dndbeyond.com/hero"

    def test_add_character_missing_player(self, managers):
        with pytest.raises(NotFoundError):
            managers.character.add_character("user-id-2", "Hero")

    def test_add_character_duplicate_name(self, managers, conn, insert_player):
        insert_player()
        managers.character.add_character("user-id-1", "Hero")
        with pytest.raises(ValidationError):
            managers.character.add_character("user-id-1", "Hero")

    def test_add_character_without_dnd_beyond_url(
        self, managers, conn, insert_player, select_character
    ):
        insert_player()
        char_id = managers.character.add_character("user-id-1", "Hero")
        assert isinstance(char_id, int)
        row = select_character(char_id)
        assert row["name"] == "Hero"
        assert row["dnd_beyond_url"] is None


class TestUpdateCharacter:
    def test_update_character_normal(
        self, managers, conn, insert_player, select_character
    ):
        insert_player()
        char_id = managers.character.add_character("user-id-1", "Hero", "url1")
        result = managers.character.update_character(
            char_id, name="Hero2", dnd_beyond_url="url2"
        )
        assert result is True
        row = select_character(char_id)
        assert row["name"] == "Hero2"
        assert row["dnd_beyond_url"] == "url2"

    def test_update_character_no_fields(self, managers, conn, insert_player):
        insert_player()
        char_id = managers.character.add_character("user-id-1", "Hero")
        with pytest.raises(ValidationError):
            managers.character.update_character(char_id)

    def test_update_character_not_found(self, managers):
        with pytest.raises(NotFoundError):
            managers.character.update_character(9999, name="NewName")

    def test_update_character_duplicate_name(self, managers, conn, insert_player):
        insert_player()
        managers.character.add_character("user-id-1", "Hero")
        char2_id = managers.character.add_character("user-id-1", "Hero2")
        with pytest.raises(ValidationError):
            managers.character.update_character(char2_id, name="Hero")


class TestRemoveCharacter:
    def test_remove_character_normal(
        self, managers, conn, insert_player, select_character
    ):
        insert_player()
        char_id = managers.character.add_character("user-id-1", "Hero")
        result = managers.character.remove_character(char_id)
        assert result is True
        row = select_character(char_id)
        assert row is None

    def test_remove_character_not_found(self, managers):
        result = managers.character.remove_character(9999)
        assert result is False

    def test_remove_character_sets_campaignplayers_null(
        self, managers, conn, insert_player, select_character
    ):
        insert_player()
        char_id = managers.character.add_character("user-id-1", "Hero")

        # Simulate a campaign with a character assigned to player
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO Campaigns (server_id, campaign_name, owner_id) VALUES (?, ?, ?)",
            ("server1", "Epic Quest", "owner1"),
        )
        campaign_id = cur.lastrowid
        cur.execute(
            "INSERT INTO CampaignPlayers (campaign_id, player_id, character_id) VALUES (?, ?, ?)",
            (campaign_id, "user-id-1", char_id),
        )
        conn.commit()

        # Deleting the character should set character_id to NULL in CampaignPlayers
        managers.character.remove_character(char_id)

        cur = conn.cursor()
        cur.execute("SELECT * FROM CampaignPLayers WHERE player_id = ?", ("user-id-1",))
        row = cur.fetchone()

        assert row is not None and row[3] is None


class TestGetCharactersForPlayer:
    def test_get_characters_for_player_normal(
        self, managers, conn, insert_player, select_character
    ):
        # Create player and multiple characters
        insert_player()
        managers.character.add_character("user-id-1", "Hero", "url1")
        managers.character.add_character("user-id-1", "Hero2", "url2")
        chars = managers.character.get_characters_for_player("user-id-1")
        assert isinstance(chars, list)
        assert len(chars) == 2
        names = {c["name"] for c in chars}
        assert "Hero" in names and "Hero2" in names

    def test_get_characters_for_player_no_characters(
        self, managers, conn, insert_player
    ):
        insert_player()
        chars = managers.character.get_characters_for_player("user-id-1")
        assert chars == []

    def test_get_characters_for_player_nonexistent_player(self, managers):
        chars = managers.character.get_characters_for_player("nonexistent")
        assert chars == []
