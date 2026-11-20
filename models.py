import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    contacts = db.relationship("Contact", backref="user", cascade="all, delete-orphan", lazy=True, order_by="desc(Contact.is_primary), Contact.name")
    diet_profile = db.relationship("DietProfile", backref="user", uselist=False, cascade="all, delete-orphan", lazy=True)
    allergies = db.relationship("Allergy", backref="user", cascade="all, delete-orphan", lazy=True)
    meal_plans = db.relationship("MealPlan", backref="user", cascade="all, delete-orphan", lazy=True, order_by="desc(MealPlan.created_at)")
    alerts = db.relationship("Alert", backref="user", cascade="all, delete-orphan", lazy=True, order_by="desc(Alert.created_at)")
    reminder_settings = db.relationship("ReminderSetting", backref="user", uselist=False, cascade="all, delete-orphan", lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_primary_contact(self):
        for c in self.contacts:
            if c.is_primary:
                return c
        return self.contacts[0] if self.contacts else None

    def __repr__(self):
        return f"<User {self.email}>"


class Contact(db.Model):
    __tablename__ = "contacts"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    telegram_chat_id = db.Column(db.String(64), nullable=True)
    relationship = db.Column(db.String(64), nullable=True)
    is_primary = db.Column(db.Boolean, default=False)
    
    deliveries = db.relationship("AlertDelivery", backref="contact", cascade="all, delete-orphan", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "telegram_chat_id": self.telegram_chat_id,
            "relationship": self.relationship or "Contact",
            "is_primary": self.is_primary
        }

    def __repr__(self):
        return f"<Contact {self.name} ({self.relationship})>"


class DietProfile(db.Model):
    __tablename__ = "diet_profiles"
    
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    diet_type = db.Column(db.String(30), default="veg", nullable=False)  # veg, vegan, non-veg
    dislikes = db.Column(db.Text, default="", nullable=False)  # comma-separated or text
    restrictions = db.Column(db.Text, default="", nullable=False)  # low-sodium, diabetic-friendly, soft-food
    conditions_note = db.Column(db.Text, default="", nullable=True)
    clinician_note = db.Column(db.Text, default="", nullable=True)
    
    def get_dislikes_list(self):
        if not self.dislikes:
            return []
        return [item.strip().lower() for item in self.dislikes.split(",") if item.strip()]

    def get_restrictions_list(self):
        if not self.restrictions:
            return []
        return [item.strip().lower() for item in self.restrictions.split(",") if item.strip()]

    def __repr__(self):
        return f"<DietProfile User:{self.user_id} Type:{self.diet_type}>"


class Allergy(db.Model):
    __tablename__ = "allergies"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return f"<Allergy {self.name}>"


class MealPlan(db.Model):
    __tablename__ = "meal_plans"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_date = db.Column(db.String(20), nullable=False)  # e.g. "2026-10-26"
    plan_json = db.Column(db.Text, nullable=False)  # JSON representation of 4 meals
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_plan_data(self):
        try:
            return json.loads(self.plan_json)
        except Exception:
            return {}

    def __repr__(self):
        return f"<MealPlan User:{self.user_id} Date:{self.plan_date}>"


class Alert(db.Model):
    __tablename__ = "alerts"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    message = db.Column(db.Text, nullable=False)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    location_status = db.Column(db.String(40), default="unavailable")  # 'available', 'denied', 'timeout', 'unavailable'
    mode = db.Column(db.String(20), default="test")  # 'test' or 'live'
    overall_status = db.Column(db.String(30), default="pending")  # 'pending', 'sent', 'partial', 'failed'
    
    deliveries = db.relationship("AlertDelivery", backref="alert", cascade="all, delete-orphan", lazy=True)
    
    def get_maps_link(self):
        if self.lat is not None and self.lng is not None:
            return f"https://www.google.com/maps?q={self.lat},{self.lng}"
        return None

    def __repr__(self):
        return f"<Alert #{self.id} Mode:{self.mode} Status:{self.overall_status}>"


class AlertDelivery(db.Model):
    __tablename__ = "alert_deliveries"
    
    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.Integer, db.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    provider = db.Column(db.String(40), nullable=False)  # 'console', 'telegram', 'twilio'
    status = db.Column(db.String(30), nullable=False)  # 'sent', 'failed'
    provider_ref = db.Column(db.String(120), nullable=True)
    error = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AlertDelivery Alert:{self.alert_id} Provider:{self.provider} Status:{self.status}>"


class ReminderSetting(db.Model):
    __tablename__ = "reminder_settings"
    
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    meals_enabled = db.Column(db.Boolean, default=True)
    meal_times_json = db.Column(db.Text, default='{"breakfast": "08:30", "lunch": "13:00", "snacks": "16:30", "dinner": "19:30"}')
    water_enabled = db.Column(db.Boolean, default=True)
    water_interval_min = db.Column(db.Integer, default=60)
    
    def get_meal_times(self):
        try:
            return json.loads(self.meal_times_json)
        except Exception:
            return {"breakfast": "08:30", "lunch": "13:00", "snacks": "16:30", "dinner": "19:30"}

    def __repr__(self):
        return f"<ReminderSetting User:{self.user_id}>"
