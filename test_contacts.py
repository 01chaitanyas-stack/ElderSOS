import pytest
from app import create_app
from models import db, User, Contact
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    ALERT_MODE = "test"

@pytest.fixture
def client_with_user():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        # Create test user
        user = User(name="Senior Ramesh", email="ramesh@example.com", age=70)
        user.set_password("pass123")
        db.session.add(user)
        db.session.commit()
        
        client = app.test_client()
        # Log in the user
        client.post("/login", data={"email": "ramesh@example.com", "password": "pass123"})
        
        yield client, user
        db.session.remove()
        db.drop_all()

def test_contacts_crud(client_with_user):
    client, user = client_with_user
    
    # 1. Add first contact (should auto-become primary)
    response = client.post("/contacts/add", data={
        "name": "Arjun Sharma",
        "relationship": "Son",
        "phone": "+91 98765 43210",
        "telegram_chat_id": "123456789"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Arjun Sharma" in response.data
    
    contact1 = Contact.query.filter_by(name="Arjun Sharma").first()
    assert contact1 is not None
    assert contact1.is_primary is True
    assert contact1.telegram_chat_id == "123456789"
    
    # 2. Add second contact without primary flag
    response = client.post("/contacts/add", data={
        "name": "Dr. Verma",
        "relationship": "Doctor",
        "phone": "9876543211",
        "telegram_chat_id": ""
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Dr. Verma" in response.data
    
    contact2 = Contact.query.filter_by(name="Dr. Verma").first()
    assert contact2 is not None
    assert contact2.is_primary is False
    
    # 3. Edit second contact and make it primary
    response = client.post(f"/contacts/{contact2.id}/edit", data={
        "name": "Dr. Rajesh Verma",
        "relationship": "Doctor",
        "phone": "+91 9876543211",
        "telegram_chat_id": "999888777",
        "is_primary": "y"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Updated details" in response.data
    assert b"Dr. Rajesh Verma" in response.data
    
    # Check that contact2 is now primary and contact1 is demoted
    db.session.refresh(contact1)
    db.session.refresh(contact2)
    assert contact2.is_primary is True
    assert contact1.is_primary is False
    
    # 4. Make contact1 primary again via quick endpoint
    response = client.post(f"/contacts/{contact1.id}/make-primary", follow_redirects=True)
    assert response.status_code == 200
    db.session.refresh(contact1)
    db.session.refresh(contact2)
    assert contact1.is_primary is True
    assert contact2.is_primary is False
    
    # 5. Delete contact
    response = client.post(f"/contacts/{contact2.id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert db.session.get(Contact, contact2.id) is None

def test_contact_validation(client_with_user):
    client, user = client_with_user
    
    # Test invalid phone number (too short)
    res = client.post("/contacts/add", data={
        "name": "Bad Contact",
        "relationship": "Other",
        "phone": "123",
        "telegram_chat_id": ""
    }, follow_redirects=True)
    assert b"Please enter a valid phone number" in res.data
    
    # Test invalid telegram ID (letters instead of digits)
    res2 = client.post("/contacts/add", data={
        "name": "Bad Contact 2",
        "relationship": "Other",
        "phone": "+91 9876543210",
        "telegram_chat_id": "not_numeric_id"
    }, follow_redirects=True)
    assert b"Telegram Chat ID should be numeric" in res2.data
