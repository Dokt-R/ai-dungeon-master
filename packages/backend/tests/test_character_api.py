import pytest
import sqlite3
import uuid
import os
import tempfile


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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Players (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            last_active_campaign TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Characters (
            character_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id TEXT NOT NULL,
            name TEXT NOT NULL,
            dnd_beyond_url TEXT,
            FOREIGN KEY (player_id) REFERENCES Players(user_id),
            UNIQUE(player_id, name)
        )
    """)
    conn.commit()
    conn.close()


@pytest.fixture(autouse=True)
def clear_tables(temp_db_file, set_db_env_and_schema):
    conn = sqlite3.connect(temp_db_file)
    cur = conn.cursor()
    for table in ["Characters", "Players"]:
        try:
            cur.execute(f"DELETE FROM {table}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()


@pytest.fixture
def player_id(client):
    test_player_id = str(uuid.uuid4())
    username = "TestUser"
    resp = client.post(
        "/players/create", json={"user_id": test_player_id, "username": username}
    )
    assert resp.status_code == 200
    return test_player_id


@pytest.fixture
def client(temp_db_file, set_db_env_and_schema):
    from packages.backend.main import app
    from fastapi.testclient import TestClient

    return TestClient(app)


def test_add_character(client, player_id):
    response = client.post(
        "/characters/add",
        json={
            "player_id": player_id,
            "name": "TestChar",
            "dnd_beyond_url": "http://example.com",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "character_id" in data


def test_add_character_invalid_name(client, player_id):
    # Too short
    resp = client.post("/characters/add", json={"player_id": player_id, "name": ""})
    assert resp.status_code == 422
    # Too long
    resp = client.post(
        "/characters/add", json={"player_id": player_id, "name": "A" * 33}
    )
    assert resp.status_code == 422
    # Invalid characters
    resp = client.post(
        "/characters/add", json={"player_id": player_id, "name": "Invalid!@#"}
    )
    assert resp.status_code == 422


def test_add_character_missing_fields(client):
    resp = client.post("/characters/add", json={})
    assert resp.status_code == 422


def test_add_character_not_found_player(client):
    resp = client.post(
        "/characters/add", json={"player_id": "nonexistent", "name": "Hero"}
    )
    assert resp.status_code == 404
    assert "does not exist" in resp.text


def test_update_character_not_found(client, player_id):
    resp = client.post(
        "/characters/update", json={"character_id": 99999, "name": "NewName"}
    )
    assert resp.status_code == 404
    assert "does not exist" in resp.text


def test_update_character_duplicate_name(client, player_id):
    # Add two characters
    resp1 = client.post(
        "/characters/add", json={"player_id": player_id, "name": "Char1"}
    )
    resp2 = client.post(
        "/characters/add", json={"player_id": player_id, "name": "Char2"}
    )
    char2_id = resp2.json()["character_id"]
    # Try to rename Char2 to Char1
    resp = client.post(
        "/characters/update", json={"character_id": char2_id, "name": "Char1"}
    )
    assert resp.status_code == 400
    assert "already exists" in resp.text


def test_add_duplicate_character(client, player_id):
    client.post("/characters/add", json={"player_id": player_id, "name": "DupChar"})
    response = client.post(
        "/characters/add", json={"player_id": player_id, "name": "DupChar"}
    )
    assert response.status_code == 400


def test_list_characters(client, player_id):
    client.post("/characters/add", json={"player_id": player_id, "name": "ListChar"})
    response = client.post("/characters/list", json={"player_id": player_id})
    assert response.status_code == 200
    data = response.json()
    assert "characters" in data
    assert any(c["name"] == "ListChar" for c in data["characters"])


def test_update_character(client, player_id):
    add_resp = client.post(
        "/characters/add", json={"player_id": player_id, "name": "UpdatableChar"}
    )
    char_id = add_resp.json()["character_id"]
    response = client.post(
        "/characters/update", json={"character_id": char_id, "name": "UpdatedChar"}
    )
    assert response.status_code == 200
    list_resp = client.post("/characters/list", json={"player_id": player_id})
    chars = list_resp.json()["characters"]
    assert any(c["name"] == "UpdatedChar" for c in chars)


def test_remove_character(client, player_id):
    add_resp = client.post(
        "/characters/add", json={"player_id": player_id, "name": "RemovableChar"}
    )
    char_id = add_resp.json()["character_id"]
    response = client.post("/characters/remove", json={"character_id": char_id})
    assert response.status_code == 200
    list_resp = client.post("/characters/list", json={"player_id": player_id})
    chars = list_resp.json()["characters"]
    assert not any(c["character_id"] == char_id for c in chars)


def test_join_campaign_with_character(client, player_id, temp_db_file):
    # Create required tables for campaign join logic
    conn = sqlite3.connect(temp_db_file)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Campaigns (
            campaign_id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id TEXT NOT NULL,
            campaign_name TEXT NOT NULL,
            owner_id TEXT,
            state TEXT,
            UNIQUE(server_id, campaign_name)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS CampaignPlayers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            player_id TEXT NOT NULL,
            character_id INTEGER,
            player_status TEXT,
            FOREIGN KEY (campaign_id) REFERENCES Campaigns(campaign_id),
            FOREIGN KEY (player_id) REFERENCES Players(user_id),
            FOREIGN KEY (character_id) REFERENCES Characters(character_id),
            UNIQUE(campaign_id, player_id)
        )
    """)
    # Insert a campaign
    server_id = "test-server"
    campaign_name = "Test Campaign"
    cur.execute(
        "INSERT INTO Campaigns (server_id, campaign_name, owner_id, state) VALUES (?, ?, ?, ?)",
        (server_id, campaign_name, "owner1", "active"),
    )
    conn.commit()
    conn.close()

    # Join campaign with character data
    join_payload = {
        "server_id": server_id,
        "campaign_name": campaign_name,
        "player_id": player_id,
        "character_name": "Hero",
        "dnd_beyond_url": "http://dndbeyond.com/hero",
    }
    resp = client.post("/players/join_campaign", json=join_payload)
    assert resp.status_code == 200
    data = resp.json()["result"]
    assert data["campaign_name"] == campaign_name
    assert data["player_id"] == player_id
    assert data["character_id"] is not None
    assert data["status"] == "joined"
