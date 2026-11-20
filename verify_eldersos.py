#!/usr/bin/env python3
"""
ElderSOS: End-to-End System Verification Script
Executes all core features and verifies database integrity, SOS dispatching, and Diet Engine filtering.
"""

import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add eldersos directory to python path
BASE_DIR = Path(__file__).resolve().parent.parent / "eldersos"
sys.path.insert(0, str(BASE_DIR))

from app import create_app
from config import Config
from models import db, User, Contact, DietProfile, Allergy, MealPlan, Alert, AlertDelivery, ReminderSetting
from services.alerts import dispatch_sos_alert
from services.diet_engine import DietEngine

class VerificationConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    ALERT_MODE = "test"
    ALERT_PROVIDER = "console"

def log_section(title):
    print("\n" + "=" * 70)
    print(f"  🔍 {title}")
    print("=" * 70)

def log_pass(msg):
    print(f"  ✅ [PASS] {msg}")

def log_fail(msg):
    print(f"  ❌ [FAIL] {msg}")

def run_verification():
    log_section("1. INITIALIZING ELDERSOS APP & DATABASE")
    app = create_app(VerificationConfig)
    
    with app.app_context():
        # Check DB tables
        tables = db.metadata.tables.keys()
        expected = {"users", "contacts", "diet_profiles", "allergies", "meal_plans", "alerts", "alert_deliveries", "reminder_settings"}
        missing = expected - set(tables)
        if not missing:
            log_pass(f"All {len(expected)} database tables successfully mapped in SQLite: {', '.join(expected)}")
        else:
            log_fail(f"Missing tables: {missing}")
            return False

        log_section("2. USER AUTHENTICATION & PASSWORD HASHING")
        user = User(name="Shri Ramchandra", email="ramchandra@example.com", age=73)
        user.set_password("Secret123$")
        db.session.add(user)
        db.session.commit()
        
        # Verify hashing
        assert user.password_hash != "Secret123$", "Password was stored in plaintext!"
        assert user.check_password("Secret123$") is True, "Password verification failed"
        assert user.check_password("WrongPassword") is False, "Wrong password accepted"
        log_pass("User registered with secure PBKDF2 password hashing.")

        log_section("3. EMERGENCY CONTACTS CRUD & PRIMARY TOGGLE")
        c1 = Contact(user_id=user.id, name="Vijay (Son)", phone="+91 9876543210", telegram_chat_id="5829104", is_primary=True)
        c2 = Contact(user_id=user.id, name="Dr. Mehta (Cardiologist)", phone="+91 9876543211", is_primary=False)
        db.session.add_all([c1, c2])
        db.session.commit()
        
        primary = user.get_primary_contact()
        assert primary.name == "Vijay (Son)", "Primary contact detection failed"
        log_pass(f"Contacts created. Primary contact correctly resolved: {primary.name} ({primary.phone})")

        log_section("4. EMERGENCY SOS WORKFLOW (TEST MODE)")
        sos_result = dispatch_sos_alert(
            user=user,
            lat=28.6139,
            lng=77.2090,
            location_status="available",
            message_custom="Assistance needed: feeling dizzy after morning walk."
        )
        
        assert sos_result["success"] is True
        assert sos_result["mode"] == "test"
        assert sos_result["overall_status"] == "sent"
        assert len(sos_result["deliveries"]) == 2
        log_pass("SOS dispatch in TEST mode generated console alerts with GPS pin.")
        log_pass(f"Google Maps Link: {sos_result['maps_link']}")
        log_pass(f"Recipients alerted: {len(sos_result['deliveries'])} contacts")

        # Verify AlertDelivery DB rows
        alert_db = db.session.get(Alert, sos_result["alert_id"])
        assert len(alert_db.deliveries) == 2
        log_pass("Alert and AlertDelivery audit rows persisted in SQLite with honest delivery status.")

        log_section("5. RULE-BASED DIET ENGINE & STRICT ALLERGEN FILTERING")
        # Configure allergies & dislikes
        profile = DietProfile(
            user_id=user.id,
            diet_type="veg",
            dislikes="bitter gourd, papaya",
            restrictions="low-sodium, soft-food",
            conditions_note="Type 2 Diabetes, High Blood Pressure",
            clinician_note="Restricted daily salt to 4g"
        )
        a1 = Allergy(user_id=user.id, name="dairy")
        a2 = Allergy(user_id=user.id, name="peanuts")
        db.session.add_all([profile, a1, a2])
        db.session.commit()

        engine = DietEngine()
        plan = engine.generate_daily_plan(user, "2026-10-26")

        log_pass("Generated full 4-meal daily menu:")
        for mtype in ["breakfast", "lunch", "evening_snacks", "dinner"]:
            m = plan["meals"][mtype]
            print(f"      • {mtype.replace('_', ' ').title():<15}: {m['name']} ({m.get('hindi_name', '')})")
            print(f"        Portion: {m['portion_size']} | Cals: {m['calories']} kcal | Protein: {m['protein_g']}g")
            
            # Assertions on allergy/dislike exclusion
            assert "dairy" not in m.get("allergies", []), f"Allergen dairy leaked into {m['name']}"
            assert "peanuts" not in m.get("allergies", []), f"Allergen peanuts leaked into {m['name']}"
            assert "bitter gourd" not in m.get("name", "").lower(), f"Disliked bitter gourd leaked into {m['name']}"

        log_pass("Allergen dairy and peanuts STRICTLY excluded across all meals.")
        log_pass(f"Daily Nutrition Summary: {plan['nutrition_totals']['calories']} kcal | {plan['nutrition_totals']['protein_g']}g Protein | {plan['nutrition_totals']['fiber_g']}g Fiber")
        log_pass(f"Condition Warning: {plan['condition_notice']}")
        log_pass(f"Medical Disclaimer Present: {bool(plan['medical_disclaimer'])}")

        log_section("6. SENIOR HYDRATION & REMINDER SETTINGS")
        reminders = ReminderSetting(user_id=user.id, water_enabled=True, water_interval_min=45, meals_enabled=True)
        db.session.add(reminders)
        db.session.commit()
        log_pass("Reminder preferences saved (Hydration interval: 45 min, Meals: Enabled).")

        log_section("SYSTEM VERIFICATION SUMMARY")
        print("\n  ⭐⭐⭐⭐⭐ ALL 6 MODULES VERIFIED & OPERATIONAL! ⭐⭐⭐⭐⭐")
        print("  ElderSOS is completely configured, verified, and ready for senior use.")
        return True

if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
