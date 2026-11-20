import pytest
from unittest.mock import patch, MagicMock
from app import create_app
from models import db, User, Contact, Alert, AlertDelivery
from config import Config

class TestSosConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    ALERT_MODE = "test"
    ALERT_PROVIDER = "console"

@pytest.fixture
def sos_client():
    app = create_app(TestSosConfig)
    with app.app_context():
        db.create_all()
        # Create user
        user = User(name="Senior Sita", email="sita@example.com", age=68)
        user.set_password("pass123")
        db.session.add(user)
        db.session.commit()

        client = app.test_client()
        client.post("/login", data={"email": "sita@example.com", "password": "pass123"})
        
        yield client, user, app
        db.session.remove()
        db.drop_all()

def test_sos_test_mode_with_contacts(sos_client):
    client, user, app = sos_client
    
    # Add two emergency contacts
    with app.app_context():
        c1 = Contact(user_id=user.id, name="Kavita (Daughter)", phone="+91 9876543210", is_primary=True)
        c2 = Contact(user_id=user.id, name="Rohan (Son)", phone="+91 9876543211", is_primary=False)
        db.session.add_all([c1, c2])
        db.session.commit()

    # Trigger SOS via API with GPS
    res = client.post("/api/sos", json={
        "lat": 28.6139,
        "lng": 77.2090,
        "location_status": "available"
    })
    
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["mode"] == "test"
    assert data["overall_status"] == "sent"
    assert "google.com/maps?q=28.6139,77.209" in data["maps_link"]
    assert len(data["deliveries"]) == 2
    assert data["deliveries"][0]["status"] == "sent"
    assert data["deliveries"][0]["provider"] == "console"

    # Verify DB records
    with app.app_context():
        alert = db.session.get(Alert, data["alert_id"])
        assert alert is not None
        assert alert.mode == "test"
        assert alert.overall_status == "sent"
        assert len(alert.deliveries) == 2

def test_sos_no_contacts_honest_failure(sos_client):
    client, user, app = sos_client
    
    # User has no contacts
    res = client.post("/api/sos", json={
        "lat": None,
        "lng": None,
        "location_status": "unavailable"
    })
    
    assert res.status_code == 400
    data = res.get_json()
    assert data["success"] is False
    assert data["overall_status"] == "failed"
    assert "No emergency contacts" in data["error_summary"]

def test_sos_live_mode_unconfigured_honest_failure(sos_client):
    client, user, app = sos_client
    
    # Configure live mode with Telegram but empty token
    app.config["ALERT_MODE"] = "live"
    app.config["ALERT_PROVIDER"] = "telegram"
    app.config["TELEGRAM_BOT_TOKEN"] = ""  # Not configured
    
    with app.app_context():
        c1 = Contact(user_id=user.id, name="Kavita", phone="+91 9876543210", telegram_chat_id="12345")
        db.session.add(c1)
        db.session.commit()

    res = client.post("/api/sos", json={
        "lat": None,
        "lng": None,
        "location_status": "unavailable"
    })
    
    assert res.status_code == 400
    data = res.get_json()
    assert data["success"] is False
    assert data["overall_status"] == "failed"
    assert "not configured" in data["error_summary"].lower()
    assert data["deliveries"][0]["status"] == "failed"

def test_sos_live_telegram_success_and_failure(sos_client):
    client, user, app = sos_client
    
    app.config["ALERT_MODE"] = "live"
    app.config["ALERT_PROVIDER"] = "telegram"
    app.config["TELEGRAM_BOT_TOKEN"] = "mock_token_12345"
    
    with app.app_context():
        c1 = Contact(user_id=user.id, name="Valid Chat", phone="+91 9876543210", telegram_chat_id="111222")
        c2 = Contact(user_id=user.id, name="Blocked Chat", phone="+91 9876543211", telegram_chat_id="333444")
        db.session.add_all([c1, c2])
        db.session.commit()

    # Mock requests.post to simulate Telegram API behavior
    def mock_post(url, json, timeout):
        mock_resp = MagicMock()
        if json["chat_id"] == "111222":
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"ok": True, "result": {"message_id": 9991}}
        else:
            mock_resp.status_code = 403
            mock_resp.json.return_value = {"ok": False, "description": "Forbidden: bot was blocked by the user"}
        return mock_resp

    with patch("requests.post", side_effect=mock_post):
        res = client.post("/api/sos", json={"lat": None, "lng": None, "location_status": "unavailable"})
        data = res.get_json()
        
        # Succeeded for 1, failed for 1 -> overall_status is 'partial'
        assert data["overall_status"] == "partial"
        deliveries_by_name = {d["contact_name"]: d for d in data["deliveries"]}
        assert deliveries_by_name["Valid Chat"]["status"] == "sent"
        assert deliveries_by_name["Valid Chat"]["provider_ref"] == "tg-9991"
        assert deliveries_by_name["Blocked Chat"]["status"] == "failed"
        assert "bot was blocked by the user" in deliveries_by_name["Blocked Chat"]["error"]

def test_sos_history_page(sos_client):
    client, user, app = sos_client
    
    with app.app_context():
        alert = Alert(
            user_id=user.id,
            message="Test Emergency",
            lat=19.0760,
            lng=72.8777,
            location_status="available",
            mode="test",
            overall_status="sent"
        )
        db.session.add(alert)
        db.session.commit()

    res = client.get("/sos/history")
    assert res.status_code == 200
    assert b"Emergency Alert History Log" in res.data
    assert b"Test Emergency" in res.data
    assert b"ALL SENT" in res.data
