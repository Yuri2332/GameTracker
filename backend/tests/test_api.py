from datetime import datetime, timedelta, timezone
import time

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AuthSession, PlatformConnection, SyncLog, User
from app.routers import integrations
from app.security import hash_token
from tests.conftest import register, send


def test_registration_login_and_password_hash(client):
    response = register(client)
    assert response.status_code == 201
    assert "password_hash" not in response.json()
    assert client.get("/api/auth/me").json()["email"] == "player@example.com"
    logout = send(client, "POST", "/api/auth/logout")
    assert logout.status_code == 204
    login = client.post("/api/auth/login", json={"email": "player@example.com", "password": "very-secure-test-pass"})
    assert login.status_code == 200
    assert client.get("/api/auth/me").status_code == 200


def test_user_data_isolation(client):
    assert register(client).status_code == 201
    first_game = send(client, "POST", "/api/games", json={"name": "Private Game", "platform": "PC", "cover_url": "https://images.example.test/private-cover.jpg"}).json()
    second_client = TestClient(client.app)
    second_client.get("/api/auth/csrf")
    assert register(second_client, "other@example.com", "other").status_code == 201
    assert second_client.get("/api/games").json()["total"] == 0
    assert second_client.get(f"/api/games/{first_game['id']}").status_code == 404
    assert send(second_client, "PATCH", f"/api/games/{first_game['id']}", json={"favorite": True}).status_code == 404
    second_game = send(second_client, "POST", "/api/games", json={"name": "Private Game", "platform": "PC"}).json()
    assert second_game["cover_url"] is None
    assert client.get(f"/api/games/{first_game['id']}").json()["cover_url"] == "https://images.example.test/private-cover.jpg"


def test_game_crud_and_rating_validation(client):
    assert register(client).status_code == 201
    created = send(client, "POST", "/api/games", json={"name": "Test RPG", "platform": "PC", "rating": 8.5, "favorite": True}).json()
    assert created["name"] == "Test RPG"
    assert created["favorite"] is True
    updated = send(client, "PATCH", f"/api/games/{created['id']}", json={"status": "playing", "rating": 9}).json()
    assert updated["status"] == "playing"
    invalid = send(client, "PATCH", f"/api/games/{created['id']}", json={"rating": 12})
    assert invalid.status_code == 422


def test_session_duration_and_invalid_ranges(client):
    register(client)
    game = send(client, "POST", "/api/games", json={"name": "Session Game", "platform": "PC"}).json()
    end = datetime.now(timezone.utc).replace(microsecond=0)
    start = end - timedelta(minutes=90)
    created = send(client, "POST", "/api/sessions", json={"game_id": game["id"], "started_at": start.isoformat(), "ended_at": end.isoformat()}).json()
    assert created["duration_seconds"] == 5400
    invalid = send(client, "POST", "/api/sessions", json={"game_id": game["id"], "started_at": end.isoformat(), "ended_at": start.isoformat()})
    assert invalid.status_code == 422
    assert send(client, "POST", "/api/sessions", json={"game_id": "foreign", "started_at": start.isoformat(), "ended_at": end.isoformat()}).status_code == 404


def test_timer_start_pause_resume_stop_updates_stats(client):
    register(client)
    game = send(client, "POST", "/api/games", json={"name": "Timer Game", "platform": "PC"}).json()
    started = send(client, "POST", "/api/sessions/active/start", json={"game_id": game["id"]})
    assert started.status_code == 201
    assert send(client, "POST", "/api/sessions/active/start", json={"game_id": game["id"]}).status_code == 409
    assert send(client, "POST", "/api/sessions/active/pause").json()["state"] == "paused"
    assert send(client, "POST", "/api/sessions/active/resume").json()["state"] == "running"
    time.sleep(1.05)
    stopped = send(client, "POST", "/api/sessions/active/stop")
    assert stopped.status_code == 200
    assert stopped.json()["state"] == "completed"
    assert client.get("/api/dashboard").json()["totals"]["sessions"] == 1


def test_goal_progress_is_derived_from_sessions(client):
    register(client)
    game = send(client, "POST", "/api/games", json={"name": "Goal Game", "platform": "PC"}).json()
    end = datetime.now(timezone.utc).replace(microsecond=0)
    start = end - timedelta(hours=2)
    send(client, "POST", "/api/sessions", json={"game_id": game["id"], "started_at": start.isoformat(), "ended_at": end.isoformat()})
    goal = send(client, "POST", "/api/goals", json={"title": "Two hours", "goal_type": "game_hours", "target": 2, "game_ids": [game["id"]]}).json()
    assert goal["progress"] == 2
    assert goal["percentage"] == 100
    assert send(client, "POST", "/api/goals", json={"title": "Missing game", "goal_type": "game_hours", "target": 2}).status_code == 422


def test_stats_and_export_use_account_records(client):
    register(client)
    game = send(client, "POST", "/api/games", json={"name": "Export Game", "platform": "PC", "genre": "RPG"}).json()
    end = datetime.now(timezone.utc).replace(microsecond=0)
    send(client, "POST", "/api/sessions", json={"game_id": game["id"], "started_at": (end - timedelta(minutes=45)).isoformat(), "ended_at": end.isoformat()})
    stats = client.get("/api/statistics?days=30").json()
    assert stats["total_hours"] == 0.8
    assert stats["top_games"][0]["name"] == "Export Game"
    assert b"Export Game" in client.get("/api/export?format=json").content
    assert b"Export Game" in client.get("/api/export?format=csv").content


def test_integration_failure_is_logged_without_exposing_api_key(client, db_engine, monkeypatch):
    register(client)
    with Session(db_engine) as db:
        user = db.query(User).filter_by(email="player@example.com").first()
        connection = PlatformConnection(user_id=user.id, provider="steam", external_user_id="76561198000000000", status="connected")
        db.add(connection)
        db.commit()
    monkeypatch.setattr(integrations.settings, "steam_api_key", "test-secret-key")

    def fail_request(*_args, **_kwargs):
        raise integrations.httpx.TimeoutException("timeout")

    monkeypatch.setattr(integrations.httpx, "get", fail_request)
    response = send(client, "POST", "/api/integrations/steam/sync")
    assert response.status_code == 502
    with Session(db_engine) as db:
        log = db.query(SyncLog).order_by(SyncLog.started_at.desc()).first()
        assert log.status == "failed"
        assert "test-secret-key" not in (log.message or "")
