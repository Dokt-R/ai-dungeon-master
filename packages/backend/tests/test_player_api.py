import pytest
import sqlite3
import uuid
import os
import tempfile
from packages.backend.main import app
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def temp_db_file():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.remove(path)


@pytest.fixture(scope="session", autouse=True)
def set_db_env_and_schema(temp_db_file):
    os.environ["DB_PATH"] = temp_db_file
    conn = sqlite3.connect(temp_db_file)
    cur = conn.cursor()
    # Create all required tables for player API
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Players (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            last_active_campaign TEXT
        )
    """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Characters (
            character_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id TEXT NOT NULL,
            name TEXT NOT NULL,
            character_url TEXT,
            FOREIGN KEY (player_id) REFERENCES Players(user_id),
            UNIQUE(player_id, name)
        )
    """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Campaigns (
            campaign_id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id TEXT NOT NULL,
            campaign_name TEXT NOT NULL,
            owner_id TEXT,
            state TEXT,
            last_save TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(server_id, campaign_name)
        )
    """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS CampaignPlayers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            character_id INTEGER,
            player_status TEXT CHECK(player_status IN ('joined', 'cmd')) NOT NULL DEFAULT 'joined',
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (campaign_id) REFERENCES Campaigns(campaign_id),
            FOREIGN KEY (player_id) REFERENCES Players(user_id),
            FOREIGN KEY (character_id) REFERENCES Characters(character_id),
            UNIQUE(campaign_id, player_id)
        )
    """
    )
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def clear_tables(temp_db_file, set_db_env_and_schema):
    conn = sqlite3.connect(temp_db_file)
    cur = conn.cursor()
    for table in ["CampaignPlayers", "Characters", "Players", "Campaigns"]:
        try:
            cur.execute(f"DELETE FROM {table}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()


@pytest.fixture
def client(temp_db_file, set_db_env_and_schema):
    return TestClient(app)


@pytest.fixture
def create_player(client):
    def _create_player(user_id=None, username="TestUser"):
        if user_id is None:
            user_id = str(uuid.uuid4())
        resp = client.post(
            "/players/create", json={"user_id": user_id, "username": username}
        )
        assert resp.status_code == 200
        return user_id

    return _create_player


@pytest.fixture
def create_campaign(temp_db_file):
    def _create_campaign(server_id, campaign_name, owner_id="owner1", state="active"):
        conn = sqlite3.connect(temp_db_file)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO Campaigns (server_id, campaign_name, owner_id, state)
            VALUES (?, ?, ?, ?)
        """,
            (server_id, campaign_name, owner_id, state),
        )
        conn.commit()
        conn.close()

    return _create_campaign


# --- Test sections for each endpoint will go below ---

# 1. /players/create


def test_create_player_success(client):
    user_id = str(uuid.uuid4())
    username = "PlayerOne"
    resp = client.post(
        "/players/create", json={"user_id": user_id, "username": username}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == user_id
    assert data["username"] == username

    # Check DB persistence
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    cur.execute("SELECT user_id, username FROM Players WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    assert row == (user_id, username)
    conn.close()


def test_create_player_duplicate(client):
    user_id = str(uuid.uuid4())
    username = "PlayerDup"
    resp1 = client.post(
        "/players/create", json={"user_id": user_id, "username": username}
    )
    assert resp1.status_code == 200
    resp2 = client.post(
        "/players/create", json={"user_id": user_id, "username": username}
    )
    assert resp2.status_code == 200
    # Should not create duplicate
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM Players WHERE user_id = ?", (user_id,))
    count = cur.fetchone()[0]
    assert count == 1
    conn.close()


@pytest.mark.parametrize(
    "payload,field",
    [
        ({"username": "ValidName"}, "user_id"),
        ({"user_id": "abc"}, "username"),
        ({}, "user_id"),
        ({"user_id": "a", "username": "ValidName"}, "user_id"),
        ({"user_id": "validid", "username": "a"}, "username"),
        ({"user_id": "invalid id!", "username": "ValidName"}, "user_id"),
        ({"user_id": "validid", "username": "Invalid!@#"}, "username"),
    ],
)
def test_create_player_validation_errors(client, payload, field):
    resp = client.post("/players/create", json=payload)
    assert resp.status_code == 422
    assert field in resp.text


# 2. /players/join_campaign


def test_join_campaign_success(client, create_player, create_campaign):
    user_id = create_player()
    server_id = "server1"
    campaign_name = "EpicQuest"
    create_campaign(server_id, campaign_name)
    payload = {
        "server_id": server_id,
        "campaign_name": campaign_name,
        "player_id": user_id,
        "character_name": "Hero",
        "character_url": "http://dndbeyond.com/hero",
    }
    resp = client.post("/players/join_campaign", json=payload)
    assert resp.status_code == 200
    data = resp.json()["result"]
    assert data["campaign_name"] == campaign_name
    assert data["player_id"] == user_id
    assert data["character_id"] is not None
    assert data["status"] == "joined"

    # DB checks
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    # Player in CampaignPlayers
    cur.execute(
        """
        SELECT cp.player_id, c.campaign_name, cp.player_status
        FROM CampaignPlayers cp
        JOIN Campaigns c ON cp.campaign_id = c.campaign_id
        WHERE cp.player_id = ? AND c.campaign_name = ?
    """,
        (user_id, campaign_name),
    )
    row = cur.fetchone()
    assert row and row[0] == user_id and row[1] == campaign_name and row[2] == "joined"
    # Character created
    cur.execute(
        "SELECT name, character_url FROM Characters WHERE player_id = ? AND name = ?",
        (user_id, "Hero"),
    )
    char_row = cur.fetchone()
    assert (
        char_row
        and char_row[0] == "Hero"
        and char_row[1] == "http://dndbeyond.com/hero"
    )
    conn.close()


def test_join_campaign_nonexistent_campaign(client, create_player):
    user_id = create_player()
    payload = {
        "server_id": "serverX",
        "campaign_name": "DoesNotExist",
        "player_id": user_id,
        "character_name": "Hero",
    }
    resp = client.post("/players/join_campaign", json=payload)
    assert resp.status_code == 404
    assert "does not exist" in resp.text


def test_join_campaign_already_joined(client, create_player, create_campaign):
    user_id = create_player()
    server_id = "server1"
    campaign_name = "EpicQuest"
    create_campaign(server_id, campaign_name)
    payload = {
        "server_id": server_id,
        "campaign_name": campaign_name,
        "player_id": user_id,
        "character_name": "Hero",
    }
    resp1 = client.post("/players/join_campaign", json=payload)
    assert resp1.status_code == 200
    resp2 = client.post("/players/join_campaign", json=payload)
    assert resp2.status_code in (400, 422)
    assert "already joined" in resp2.text or "already" in resp2.text


@pytest.mark.parametrize(
    "payload,field",
    [
        ({"campaign_name": "EpicQuest", "player_id": "pid"}, "server_id"),
        ({"server_id": "server1", "player_id": "pid"}, "campaign_name"),
        ({"server_id": "server1", "campaign_name": "EpicQuest"}, "player_id"),
        (
            {"server_id": "s", "campaign_name": "EpicQuest", "player_id": "pid"},
            "server_id",
        ),
        (
            {"server_id": "server1", "campaign_name": "", "player_id": "pid"},
            "campaign_name",
        ),
        (
            {"server_id": "server1", "campaign_name": "EpicQuest", "player_id": "p"},
            "player_id",
        ),
        (
            {
                "server_id": "server1",
                "campaign_name": "EpicQuest",
                "player_id": "pid",
                "character_name": "",
            },
            "character_name",
        ),
        (
            {
                "server_id": "server1",
                "campaign_name": "EpicQuest",
                "player_id": "pid",
                "character_name": "Invalid!@#",
            },
            "character_name",
        ),
    ],
)
def test_join_campaign_validation_errors(client, payload, field):
    resp = client.post("/players/join_campaign", json=payload)
    assert resp.status_code == 422
    assert field in resp.text


def test_join_campaign_existing_character(
    client, create_player, create_campaign, temp_db_file
):
    user_id = create_player()
    server_id = "server1"
    campaign_name = "EpicQuest"
    create_campaign(server_id, campaign_name)
    # Pre-create character
    conn = sqlite3.connect(temp_db_file)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Characters (player_id, name, character_url) VALUES (?, ?, ?)",
        (user_id, "Hero", "http://dndbeyond.com/hero"),
    )
    conn.commit()
    conn.close()
    payload = {
        "server_id": server_id,
        "campaign_name": campaign_name,
        "player_id": user_id,
        "character_name": "Hero",
    }
    resp = client.post("/players/join_campaign", json=payload)
    assert resp.status_code == 200
    data = resp.json()["result"]
    assert data["character_id"] is not None


# 3. /players/end_campaign


def test_end_campaign_success(client, create_player, create_campaign):
    user_id = create_player()
    server_id = "server1"
    campaign_name = "EpicQuest"
    create_campaign(server_id, campaign_name)
    # Join campaign first
    join_payload = {
        "server_id": server_id,
        "campaign_name": campaign_name,
        "player_id": user_id,
        "character_name": "Hero",
    }
    client.post("/players/join_campaign", json=join_payload)
    # End campaign
    end_payload = {
        "server_id": server_id,
        "campaign_name": campaign_name,
        "player_id": user_id,
    }
    resp = client.post("/players/end_campaign", json=end_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Campaign exited successfully."
    assert "narrative" in data

    # DB check: player_status should be 'cmd'
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    cur.execute(
        """
        SELECT cp.player_status
        FROM CampaignPlayers cp
        JOIN Campaigns c ON cp.campaign_id = c.campaign_id
        WHERE cp.player_id = ? AND c.campaign_name = ?
    """,
        (user_id, campaign_name),
    )
    row = cur.fetchone()
    assert row and row[0] == "cmd"
    conn.close()


def test_end_campaign_nonexistent_campaign(client, create_player):
    user_id = create_player()
    payload = {
        "server_id": "serverX",
        "campaign_name": "DoesNotExist",
        "player_id": user_id,
    }
    resp = client.post("/players/end_campaign", json=payload)
    assert resp.status_code == 404
    assert "does not exist" in resp.text


def test_end_campaign_no_last_active(client, create_player):
    user_id = create_player()
    payload = {"server_id": "server1", "campaign_name": "", "player_id": user_id}
    # Remove campaign_name to trigger last_active_campaign logic
    payload.pop("campaign_name")
    resp = client.post("/players/end_campaign", json=payload)
    assert (
        resp.status_code == 422
        or resp.status_code == 404
        or "no last active" in resp.text.lower()
    )


def test_end_campaign_player_never_joined(client, create_player, create_campaign):
    user_id = create_player()
    server_id = "server1"
    campaign_name = "EpicQuest"
    create_campaign(server_id, campaign_name)
    # Player never joined, should not error, but no update
    payload = {
        "server_id": server_id,
        "campaign_name": campaign_name,
        "player_id": user_id,
    }
    resp = client.post("/players/end_campaign", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Campaign exited successfully."
    # DB: There should be no CampaignPlayers row for this player/campaign
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM CampaignPlayers cp
        JOIN Campaigns c ON cp.campaign_id = c.campaign_id
        WHERE cp.player_id = ? AND c.campaign_name = ?
    """,
        (user_id, campaign_name),
    )
    assert cur.fetchone() is None
    conn.close()


@pytest.mark.parametrize(
    "payload,field",
    [
        ({"campaign_name": "EpicQuest", "player_id": "pid"}, "server_id"),
        ({"server_id": "server1", "player_id": "pid"}, "campaign_name"),
        ({"server_id": "server1", "campaign_name": "EpicQuest"}, "player_id"),
        (
            {"server_id": "s", "campaign_name": "EpicQuest", "player_id": "pid"},
            "server_id",
        ),
        (
            {"server_id": "server1", "campaign_name": "", "player_id": "pid"},
            "campaign_name",
        ),
        (
            {"server_id": "server1", "campaign_name": "EpicQuest", "player_id": "p"},
            "player_id",
        ),
    ],
)
def test_end_campaign_validation_errors(client, payload, field):
    resp = client.post("/players/end_campaign", json=payload)
    assert resp.status_code == 422
    assert field in resp.text


# 4. /players/continue_campaign


@pytest.mark.skip(reason="continue_campaign endpoint is not implemented")
def test_continue_campaign_success(client, create_player, create_campaign):
    user_id = create_player()
    server_id = "server1"
    campaign_name = "EpicQuest"
    create_campaign(server_id, campaign_name)
    # Join campaign first
    join_payload = {
        "server_id": server_id,
        "campaign_name": campaign_name,
        "player_id": user_id,
        "character_name": "Hero",
    }
    client.post("/players/join_campaign", json=join_payload)
    # End campaign to simulate a paused state
    end_payload = {
        "server_id": server_id,
        "campaign_name": campaign_name,
        "player_id": user_id,
    }
    client.post("/players/end_campaign", json=end_payload)
    # Continue campaign
    continue_payload = {
        "server_id": server_id,
        "campaign_name": campaign_name,
        "player_id": user_id,
    }
    resp = client.post("/players/continue_campaign", json=continue_payload)
    assert resp.status_code == 500
    assert "not implemented" in resp.text.lower()


@pytest.mark.skip(reason="continue_campaign endpoint is not implemented")
def test_continue_campaign_nonexistent_campaign(client, create_player):
    user_id = create_player()
    payload = {
        "server_id": "serverX",
        "campaign_name": "DoesNotExist",
        "player_id": user_id,
    }
    resp = client.post("/players/continue_campaign", json=payload)
    assert resp.status_code == 500
    assert "not implemented" in resp.text.lower()


@pytest.mark.skip(reason="continue_campaign endpoint is not implemented")
def test_continue_campaign_nonexistent_player(client, create_campaign):
    user_id = str(uuid.uuid4())
    server_id = "server1"
    campaign_name = "EpicQuest"
    create_campaign(server_id, campaign_name)
    payload = {
        "server_id": server_id,
        "campaign_name": campaign_name,
        "player_id": user_id,
    }
    resp = client.post("/players/continue_campaign", json=payload)
    assert resp.status_code == 500
    assert "not implemented" in resp.text.lower()


@pytest.mark.parametrize(
    "payload,field",
    [
        ({"campaign_name": "EpicQuest", "player_id": "pid"}, "server_id"),
        ({"server_id": "server1", "player_id": "pid"}, "campaign_name"),
        ({"server_id": "server1", "campaign_name": "EpicQuest"}, "player_id"),
        (
            {"server_id": "s", "campaign_name": "EpicQuest", "player_id": "pid"},
            "server_id",
        ),
        (
            {"server_id": "server1", "campaign_name": "", "player_id": "pid"},
            "campaign_name",
        ),
        (
            {"server_id": "server1", "campaign_name": "EpicQuest", "player_id": "p"},
            "player_id",
        ),
    ],
)
def test_continue_campaign_validation_errors(client, payload, field):
    resp = client.post("/players/continue_campaign", json=payload)
    assert resp.status_code == 422
    assert field in resp.text


# 5. /players/remove_campaign


def test_remove_campaign_success(client, create_player, create_campaign):
    user_id = create_player()
    server_id = "server1"
    campaign_name = "EpicQuest"
    create_campaign(server_id, campaign_name)
    # Join campaign first
    join_payload = {
        "server_id": server_id,
        "campaign_name": campaign_name,
        "player_id": user_id,
        "character_name": "Hero",
    }
    client.post("/players/join_campaign", json=join_payload)
    # Leave campaign
    leave_payload = {
        "server_id": server_id,
        "campaign_name": campaign_name,
        "player_id": user_id,
    }
    resp = client.post("/players/remove_campaign", json=leave_payload)
    assert resp.status_code == 200
    data = resp.json()["result"]
    assert data["campaign_name"] == campaign_name
    assert data["player_id"] == user_id
    assert data["status"] == "left"
    # DB: player should be removed from CampaignPlayers, last_active_campaign should be NULL
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM CampaignPlayers cp
        JOIN Campaigns c ON cp.campaign_id = c.campaign_id
        WHERE cp.player_id = ? AND c.campaign_name = ?
    """,
        (user_id, campaign_name),
    )
    assert cur.fetchone() is None
    cur.execute(
        "SELECT last_active_campaign FROM Players WHERE user_id = ?", (user_id,)
    )
    row = cur.fetchone()
    assert row[0] is None
    conn.close()


def test_remove_campaign_nonexistent_campaign(client, create_player):
    user_id = create_player()
    payload = {
        "server_id": "serverX",
        "campaign_name": "DoesNotExist",
        "player_id": user_id,
    }
    resp = client.post("/players/remove_campaign", json=payload)
    assert resp.status_code == 404
    assert "does not exist" in resp.text


def test_remove_campaign_no_last_active(client, create_player):
    user_id = create_player()
    payload = {"server_id": "server1", "campaign_name": "", "player_id": user_id}
    # Remove campaign_name to trigger last_active_campaign logic
    payload.pop("campaign_name")
    resp = client.post("/players/remove_campaign", json=payload)
    assert (
        resp.status_code == 422
        or resp.status_code == 404
        or "no last active" in resp.text.lower()
    )


def test_remove_campaign_player_never_joined(client, create_player, create_campaign):
    user_id = create_player()
    server_id = "server1"
    campaign_name = "EpicQuest"
    create_campaign(server_id, campaign_name)
    # Player never joined, should not error, but no update
    payload = {
        "server_id": server_id,
        "campaign_name": campaign_name,
        "player_id": user_id,
    }
    resp = client.post("/players/remove_campaign", json=payload)
    assert resp.status_code == 200
    data = resp.json()["result"]
    assert data["campaign_name"] == campaign_name
    assert data["player_id"] == user_id
    assert data["status"] == "left"
    # DB: There should be no CampaignPlayers row for this player/campaign
    conn = sqlite3.connect(os.environ["DB_PATH"])
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM CampaignPlayers cp
        JOIN Campaigns c ON cp.campaign_id = c.campaign_id
        WHERE cp.player_id = ? AND c.campaign_name = ?
    """,
        (user_id, campaign_name),
    )
    assert cur.fetchone() is None
    conn.close()


@pytest.mark.parametrize(
    "payload,field",
    [
        ({"campaign_name": "EpicQuest", "player_id": "pid"}, "server_id"),
        ({"server_id": "server1", "player_id": "pid"}, "campaign_name"),
        ({"server_id": "server1", "campaign_name": "EpicQuest"}, "player_id"),
        (
            {"server_id": "s", "campaign_name": "EpicQuest", "player_id": "pid"},
            "server_id",
        ),
        (
            {"server_id": "server1", "campaign_name": "", "player_id": "pid"},
            "campaign_name",
        ),
        (
            {"server_id": "server1", "campaign_name": "EpicQuest", "player_id": "p"},
            "player_id",
        ),
    ],
)
def test_remove_campaign_validation_errors(client, payload, field):
    resp = client.post("/players/remove_campaign", json=payload)
    assert resp.status_code == 422
    assert field in resp.text


# 6. /players/status/{player_id}


def test_get_player_status_success(client, create_player, create_campaign):
    user_id = create_player(username="StatusUser")
    server_id = "server1"
    campaign_name = "EpicQuest"
    create_campaign(server_id, campaign_name)
    # Join campaign and add character
    join_payload = {
        "server_id": server_id,
        "campaign_name": campaign_name,
        "player_id": user_id,
        "character_name": "Hero",
        "character_url": "http://dndbeyond.com/hero",
    }
    client.post("/players/join_campaign", json=join_payload)
    resp = client.get(f"/players/status/{user_id}")
    assert resp.status_code == 200
    data = resp.json()["player_status"]
    assert data["player_id"] == user_id
    assert data["username"] == "StatusUser"
    assert any(c["campaign_name"] == campaign_name for c in data["campaigns"])
    assert any(c["name"] == "Hero" for c in data["characters"])


def test_get_player_status_no_campaigns_or_characters(client, create_player):
    user_id = create_player(username="LonelyUser")
    resp = client.get(f"/players/status/{user_id}")
    assert resp.status_code == 200
    data = resp.json()["player_status"]
    assert data["player_id"] == user_id
    assert data["username"] == "LonelyUser"
    assert data["campaigns"] == []
    assert data["characters"] == []


def test_get_player_status_not_found(client):
    user_id = str(uuid.uuid4())
    resp = client.get(f"/players/status/{user_id}")
    assert resp.status_code == 404
    assert "not found" in resp.text


def test_get_player_status_multiple_campaigns_and_characters(
    client, create_player, create_campaign, temp_db_file
):
    user_id = create_player(username="MultiUser")
    server_id = "server1"
    create_campaign(server_id, "EpicQuest")
    create_campaign(server_id, "SideQuest")
    # Add two characters
    conn = sqlite3.connect(temp_db_file)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Characters (player_id, name, character_url) VALUES (?, ?, ?)",
        (user_id, "Hero1", "url1"),
    )
    cur.execute(
        "INSERT INTO Characters (player_id, name, character_url) VALUES (?, ?, ?)",
        (user_id, "Hero2", "url2"),
    )
    conn.commit()
    conn.close()
    # Join EpicQuest
    join_payload1 = {
        "server_id": server_id,
        "campaign_name": "EpicQuest",
        "player_id": user_id,
        "character_name": "Hero1",
    }
    client.post("/players/join_campaign", json=join_payload1)
    # End EpicQuest
    client.post(
        "/players/end_campaign",
        json={
            "server_id": server_id,
            "campaign_name": "EpicQuest",
            "player_id": user_id,
        },
    )
    # Join SideQuest
    join_payload2 = {
        "server_id": server_id,
        "campaign_name": "SideQuest",
        "player_id": user_id,
        "character_name": "Hero2",
    }
    client.post("/players/join_campaign", json=join_payload2)
    resp = client.get(f"/players/status/{user_id}")
    assert resp.status_code == 200
    data = resp.json()["player_status"]
    assert data["player_id"] == user_id
    assert data["username"] == "MultiUser"
    # Only one campaign should be "joined", the other should be "cmd"
    joined = [c for c in data["campaigns"] if c["player_status"] == "joined"]
    cmd = [c for c in data["campaigns"] if c["player_status"] == "cmd"]
    assert len(joined) == 1
    assert joined[0]["campaign_name"] == "SideQuest"
    assert any(
        c["campaign_name"] == "EpicQuest" and c["player_status"] == "cmd"
        for c in data["campaigns"]
    )
    char_names = {c["name"] for c in data["characters"]}
    assert "Hero1" in char_names
    assert "Hero2" in char_names
