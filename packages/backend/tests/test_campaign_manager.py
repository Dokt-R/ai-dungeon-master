import sqlite3
import pytest
import os
from packages.backend.components.campaign_manager import CampaignManager
from packages.backend.components.server_settings_manager import ServerSettingsManager

SHARED_MEM_URI = "file:memdb1?mode=memory&cache=shared"


# @pytest.fixture
# def setup_db():
#     # Setup schema with autosave table
#     conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
#     cur = conn.cursor()
#     cur.execute(
#         """
#         CREATE TABLE IF NOT EXISTS Players (
#             user_id TEXT PRIMARY KEY,
#             username TEXT,
#             last_active_campaign TEXT
#         )
#     """
#     )
#     cur.execute(
#         """
#         CREATE TABLE IF NOT EXISTS Campaigns (
#             campaign_id INTEGER PRIMARY KEY AUTOINCREMENT,
#             server_id TEXT NOT NULL,
#             campaign_name TEXT NOT NULL,
#             owner_id TEXT NOT NULL,
#             state TEXT,
#             last_save TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             UNIQUE(server_id, campaign_name)
#         )
#     """
#     )
#     cur.execute(
#         """
#         CREATE TABLE IF NOT EXISTS CampaignAutosaves (
#             autosave_id INTEGER PRIMARY KEY AUTOINCREMENT,
#             campaign_id INTEGER NOT NULL,
#             state TEXT,
#             autosave_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             FOREIGN KEY (campaign_id) REFERENCES Campaigns(campaign_id)
#         )
#     """
#     )
#     conn.commit()
#     conn.close()
#     yield
#     # Teardown
#     conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
#     cur = conn.cursor()
#     for table in ["CampaignAutosaves", "Campaigns", "Players"]:
#         cur.execute(f"DELETE FROM {table}")
#     conn.commit()
# conn.close()


@pytest.fixture
def managers():
    ssm = ServerSettingsManager(SHARED_MEM_URI)
    cm = CampaignManager(SHARED_MEM_URI)
    return ssm, cm


def test_set_and_get_autosave(managers):
    ssm, _ = managers
    # Create campaign
    ssm.create_campaign("server1", "TestCampaign", "owner1", state="{}")
    campaign = ssm.get_campaign("server1", "TestCampaign")
    campaign_id = campaign["campaign_id"]
    # Set autosave
    ssm.set_campaign_autosave(campaign_id, '{"progress": 1}')
    autosave = ssm.get_latest_campaign_autosave(campaign_id)
    assert autosave is not None
    assert autosave["state"] == '{"progress": 1}'


@pytest.mark.skip(reason="Test logic is wrong and must be fixed.")
def test_continue_campaign_returns_autosave_if_newer(monkeypatch, managers):
    ssm, cm = managers
    # Create player and campaign
    server_id = "server1"
    campaign_name = "TestCampaign"
    ssm.create_campaign(server_id, campaign_name, "owner1", state='{"progress": 1}')
    campaign = ssm.get_campaign(server_id, campaign_name)
    campaign_id = campaign["campaign_id"]
    # Set player last_active_campaign
    conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Players (user_id, username, last_active_campaign) VALUES (?, ?, ?)",
        ("user1", "Alice", campaign_name),
    )
    conn.commit()
    conn.close()
    # Set autosave with a newer timestamp
    ssm.set_campaign_autosave(campaign_id, '{"progress": 2}')

    # Monkeypatch last_save to be older
    def fake_get_campaign(server_id, campaign_name):
        c = campaign.copy()
        c["last_save"] = "2000-01-01 00:00:00"
        return c

    monkeypatch.setattr(ssm, "get_campaign", fake_get_campaign)

    result = cm.continue_campaign("user1", server_id)
    assert result["source"] == "autosave"
    assert result["state"] == '{"progress": 2}'


@pytest.mark.skip(reason="Test logic is wrong and must be fixed.")
def test_continue_campaign_returns_save_if_no_autosave(monkeypatch, managers):
    ssm, cm = managers
    # Create player and campaign
    ssm.create_campaign("server1", "TestCampaign", "owner1", state='{"progress": 1}')
    campaign = ssm.get_campaign("server1", "TestCampaign")
    # Set player last_active_campaign
    conn = sqlite3.connect(SHARED_MEM_URI, uri=True)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Players (user_id, username, last_active_campaign) VALUES (?, ?, ?)",
        ("user1", "Alice", "TestCampaign"),
    )
    conn.commit()
    conn.close()

    # No autosave set
    def fake_get_campaign(server_id, campaign_name):
        c = campaign.copy()
        c["last_save"] = "2100-01-01 00:00:00"
        return c

    monkeypatch.setattr(ssm, "get_campaign", fake_get_campaign)
    result = cm.continue_campaign("user1", "server1")
    assert result["source"] == "save"
    assert result["state"] == '{"progress": 1}'


def test_continue_campaign_none_if_no_last_active(managers):
    _, cm = managers
    result = cm.continue_campaign("userX", "server1")
    assert result is None
