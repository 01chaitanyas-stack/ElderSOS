import pytest
from app import create_app
from models import db, User, DietProfile, ReminderSetting
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    ALERT_MODE = "test"

@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

def test_registration_and_login(client):
    # 1. Register a senior user
    reg_response = client.post("/register", data={
        "name": "Ramesh Chandra",
        "email": "ramesh@example.com",
        "age": "72",
        "password": "securepassword123",
        "confirm_password": "securepassword123"
    }, follow_redirects=True)
    
    assert reg_response.status_code == 200
    assert b"Welcome to ElderSOS, Ramesh Chandra" in reg_response.data
    
    # Verify DB user was created with DietProfile and ReminderSetting
    user = User.query.filter_by(email="ramesh@example.com").first()
    assert user is not None
    assert user.age == 72
    assert user.check_password("securepassword123") is True
    assert user.check_password("wrongpassword") is False
    assert user.diet_profile is not None
    assert user.reminder_settings is not None
    
    # 2. Logout
    logout_response = client.get("/logout", follow_redirects=True)
    assert logout_response.status_code == 200
    assert b"safely logged out" in logout_response.data
    
    # 3. Login with valid credentials
    login_response = client.post("/login", data={
        "email": "ramesh@example.com",
        "password": "securepassword123"
    }, follow_redirects=True)
    assert login_response.status_code == 200
    assert b"Welcome back, Ramesh Chandra" in login_response.data
    
    # 4. Login with bad credentials
    client.get("/logout", follow_redirects=True)
    bad_login = client.post("/login", data={
        "email": "ramesh@example.com",
        "password": "badpassword"
    }, follow_redirects=True)
    assert b"Incorrect email or password" in bad_login.data
