import pytest
from app import create_app
from models import db, User, DietProfile, Contact, Allergy, ReminderSetting
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    ALERT_MODE = "test"

@pytest.fixture
def dashboard_client():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        user = User(name="Senior Devraj", email="devraj@example.com", age=76)
        user.set_password("pass123")
        db.session.add(user)
        db.session.flush()

        # Add profile, reminders, contact
        p = DietProfile(user_id=user.id, diet_type="veg")
        r = ReminderSetting(user_id=user.id)
        c = Contact(user_id=user.id, name="Suresh (Son)", phone="+91 9876543210", is_primary=True)
        db.session.add_all([p, r, c])
        db.session.commit()

        client = app.test_client()
        client.post("/login", data={"email": "devraj@example.com", "password": "pass123"})
        
        yield client, user, app
        db.session.remove()
        db.drop_all()

def test_dashboard_renders(dashboard_client):
    client, user, app = dashboard_client
    res = client.get("/dashboard")
    assert res.status_code == 200
    assert b"Namaste, Senior Devraj" in res.data
    assert b"Suresh (Son)" in res.data
    assert b"Senior Hydration Tracker" in res.data
    assert b"Caregiver &amp; Family Support Center" in res.data or b"Caregiver & Family Support Center" in res.data
    assert b"Call 112 Directly" in res.data or b"Dial 112" in res.data

def test_profile_update(dashboard_client):
    client, user, app = dashboard_client
    
    # Post updated profile data
    res = client.post("/profile/", data={
        "name": "Devraj Sharma",
        "age": "77",
        "diet_type": "vegan",
        "allergies": "dairy, peanuts, mustard",
        "dislikes": "papaya, bitter gourd",
        "restrictions": "low-sodium, soft-food",
        "conditions_note": "Type 2 Diabetes",
        "clinician_note": "Strict salt restriction",
        "water_enabled": "y",
        "water_interval_min": "45",
        "meals_enabled": "y"
    }, follow_redirects=True)
    
    assert res.status_code == 200
    assert b"Your profile, dietary restrictions, and reminder preferences have been updated" in res.data
    
    with app.app_context():
        u = db.session.get(User, user.id)
        assert u.name == "Devraj Sharma"
        assert u.age == 77
        assert u.diet_profile.diet_type == "vegan"
        assert "papaya" in u.diet_profile.dislikes
        assert "soft-food" in u.diet_profile.restrictions
        assert u.diet_profile.conditions_note == "Type 2 Diabetes"
        
        # Check allergies
        allergy_names = [a.name for a in u.allergies]
        assert "dairy" in allergy_names
        assert "peanuts" in allergy_names
        assert "mustard" in allergy_names
        
        # Check reminders
        assert u.reminder_settings.water_interval_min == 45
        assert u.reminder_settings.water_enabled is True
