"""
ElderSOS app.py  — SPA backend
Serves static/index.html for every non-API route and exposes JSON APIs only.
No Jinja2 templates are used; the frontend is a single-page app.
"""
import os
import re
import json
from datetime import datetime
from pathlib import Path

from flask import (Flask, send_from_directory, jsonify, request,
                   session, redirect, url_for)
from flask_login import (LoginManager, login_user, logout_user,
                         login_required, current_user)
from flask_wtf.csrf import CSRFProtect, generate_csrf
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from models import (db, User, Contact, DietProfile, Allergy,
                    MealPlan, Alert, AlertDelivery, ReminderSetting)
from services import dispatch_sos_alert, DietEngine


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(config_class=Config):
    app = Flask(
        __name__,
        static_folder="static",    # serves static/index.html, style.css, script.js, etc.
        static_url_path="/static"
    )
    app.config.from_object(config_class)

    db.init_app(app)
    csrf = CSRFProtect(app)

    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({"error": "Authentication required", "redirect": "/"}), 401

    # ------------------------------------------------------------------
    # PWA helper routes (must live at root)
    # ------------------------------------------------------------------
    @app.route("/manifest.json")
    def manifest():
        return send_from_directory(app.static_folder, "manifest.json",
                                   mimetype="application/manifest+json")

    @app.route("/sw.js")
    def service_worker():
        resp = send_from_directory(app.static_folder, "sw.js",
                                   mimetype="application/javascript")
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp

    # ------------------------------------------------------------------
    # SPA catch-all: serve index.html for every non-API, non-static path
    # ------------------------------------------------------------------
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def spa(path):
        # Let static files through
        if path.startswith("static/"):
            return send_from_directory(app.static_folder,
                                       path[len("static/"):])
        return send_from_directory(app.static_folder, "index.html")

    # ------------------------------------------------------------------
    # API: CSRF token endpoint (called once on page load)
    # ------------------------------------------------------------------
    @app.route("/api/csrf")
    def api_csrf():
        return jsonify({"csrf_token": generate_csrf()})

    # ------------------------------------------------------------------
    # API: Auth
    # ------------------------------------------------------------------
    @app.route("/api/auth/status")
    def api_auth_status():
        if current_user.is_authenticated:
            return jsonify({
                "authenticated": True,
                "user": {
                    "id": current_user.id,
                    "name": current_user.name,
                    "email": current_user.email,
                    "age": current_user.age,
                },
                "alert_mode": app.config.get("ALERT_MODE", "test"),
                "alert_provider": app.config.get("ALERT_PROVIDER", "console"),
            })
        return jsonify({"authenticated": False})

    @app.route("/api/auth/register", methods=["POST"])
    def api_register():
        data = request.get_json(silent=True) or {}
        name  = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        age   = data.get("age")
        pwd   = data.get("password") or ""
        cpwd  = data.get("confirm_password") or ""

        errors = {}
        if len(name) < 2:
            errors["name"] = "Name must be at least 2 characters."
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            errors["email"] = "Invalid email address."
        elif User.query.filter_by(email=email).first():
            errors["email"] = "An account with this email already exists."
        try:
            age = int(age)
            if age < 50 or age > 120:
                errors["age"] = "ElderSOS is designed for seniors aged 50–120."
        except (TypeError, ValueError):
            errors["age"] = "Please enter a valid age."
        if len(pwd) < 6:
            errors["password"] = "Password must be at least 6 characters."
        elif pwd != cpwd:
            errors["confirm_password"] = "Passwords do not match."

        if errors:
            return jsonify({"success": False, "errors": errors}), 400

        user = User(name=name, email=email, age=age)
        user.set_password(pwd)
        db.session.add(user)
        db.session.flush()

        db.session.add(DietProfile(user_id=user.id, diet_type="veg",
                                   dislikes="", restrictions="low-sodium"))
        db.session.add(ReminderSetting(user_id=user.id,
                                       meals_enabled=True, water_enabled=True,
                                       water_interval_min=60))
        db.session.commit()
        login_user(user)
        return jsonify({"success": True, "name": user.name})

    @app.route("/api/auth/login", methods=["POST"])
    def api_login():
        data  = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        pwd   = data.get("password") or ""
        remember = bool(data.get("remember", False))

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(pwd):
            login_user(user, remember=remember)
            return jsonify({"success": True, "name": user.name})
        return jsonify({"success": False, "error": "Incorrect email or password."}), 401

    @app.route("/api/auth/logout", methods=["POST"])
    @login_required
    def api_logout():
        logout_user()
        return jsonify({"success": True})

    # ------------------------------------------------------------------
    # API: Dashboard
    # ------------------------------------------------------------------
    @app.route("/api/dashboard")
    @login_required
    def api_dashboard():
        primary = current_user.get_primary_contact()
        contacts_count = Contact.query.filter_by(user_id=current_user.id).count()
        recent_alerts = Alert.query.filter_by(user_id=current_user.id)\
            .order_by(Alert.created_at.desc()).limit(3).all()
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        today_plan = MealPlan.query.filter_by(
            user_id=current_user.id, plan_date=today_str).first()

        return jsonify({
            "user": {
                "name": current_user.name,
                "age": current_user.age,
            },
            "alert_mode": app.config.get("ALERT_MODE", "test"),
            "primary_contact": primary.to_dict() if primary else None,
            "contacts_count": contacts_count,
            "recent_alerts": [
                {
                    "id": a.id,
                    "created_at": a.created_at.strftime("%d-%b-%Y at %I:%M %p"),
                    "mode": a.mode,
                    "overall_status": a.overall_status,
                }
                for a in recent_alerts
            ],
            "today_plan": today_plan.get_plan_data() if today_plan else None,
        })

    # ------------------------------------------------------------------
    # API: SOS
    # ------------------------------------------------------------------
    @app.route("/api/sos", methods=["POST"])
    @login_required
    def api_sos():
        data = request.get_json(silent=True) or {}
        lat = data.get("lat")
        lng = data.get("lng")
        location_status = data.get("location_status", "unavailable")
        try:
            lat = float(lat) if lat is not None else None
            lng = float(lng) if lng is not None else None
        except (ValueError, TypeError):
            lat = lng = None
            location_status = "unavailable"

        result = dispatch_sos_alert(
            user=current_user, lat=lat, lng=lng,
            location_status=location_status
        )
        return jsonify(result), (200 if result.get("success") else 400)

    @app.route("/api/sos/history")
    @login_required
    def api_sos_history():
        alerts = Alert.query.filter_by(user_id=current_user.id)\
            .order_by(Alert.created_at.desc()).all()
        result = []
        for a in alerts:
            result.append({
                "id": a.id,
                "created_at": a.created_at.strftime("%A, %d %B %Y at %I:%M:%S %p UTC"),
                "mode": a.mode,
                "overall_status": a.overall_status,
                "location_status": a.location_status,
                "lat": a.lat,
                "lng": a.lng,
                "maps_link": a.get_maps_link(),
                "message": a.message,
                "deliveries": [
                    {
                        "contact_name": d.contact.name if d.contact else "Deleted Contact",
                        "provider": d.provider,
                        "status": d.status,
                        "provider_ref": d.provider_ref,
                        "error": d.error,
                    }
                    for d in a.deliveries
                ],
            })
        return jsonify(result)

    # ------------------------------------------------------------------
    # API: Contacts
    # ------------------------------------------------------------------
    @app.route("/api/contacts", methods=["GET"])
    @login_required
    def api_contacts_list():
        contacts = Contact.query.filter_by(user_id=current_user.id)\
            .order_by(Contact.is_primary.desc(), Contact.name.asc()).all()
        return jsonify([c.to_dict() for c in contacts])

    @app.route("/api/contacts", methods=["POST"])
    @login_required
    def api_contacts_add():
        data = request.get_json(silent=True) or {}
        errors = _validate_contact(data)
        if errors:
            return jsonify({"success": False, "errors": errors}), 400

        existing = Contact.query.filter_by(user_id=current_user.id).all()
        is_first = (len(existing) == 0)
        make_primary = bool(data.get("is_primary")) or is_first

        if make_primary:
            Contact.query.filter_by(user_id=current_user.id,
                                    is_primary=True).update({"is_primary": False})

        tg = (data.get("telegram_chat_id") or "").strip() or None
        contact = Contact(
            user_id=current_user.id,
            name=data["name"].strip(),
            relationship=data.get("relationship", "Other"),
            phone=data["phone"].strip(),
            telegram_chat_id=tg,
            is_primary=make_primary,
        )
        db.session.add(contact)
        db.session.commit()
        return jsonify({"success": True, "contact": contact.to_dict()})

    @app.route("/api/contacts/<int:contact_id>", methods=["PUT"])
    @login_required
    def api_contacts_edit(contact_id):
        contact = Contact.query.filter_by(
            id=contact_id, user_id=current_user.id).first_or_404()
        data = request.get_json(silent=True) or {}
        errors = _validate_contact(data)
        if errors:
            return jsonify({"success": False, "errors": errors}), 400

        if bool(data.get("is_primary")) and not contact.is_primary:
            Contact.query.filter_by(user_id=current_user.id,
                                    is_primary=True).update({"is_primary": False})

        contact.name = data["name"].strip()
        contact.relationship = data.get("relationship", "Other")
        contact.phone = data["phone"].strip()
        contact.telegram_chat_id = (data.get("telegram_chat_id") or "").strip() or None
        contact.is_primary = bool(data.get("is_primary"))
        db.session.commit()
        return jsonify({"success": True, "contact": contact.to_dict()})

    @app.route("/api/contacts/<int:contact_id>/make-primary", methods=["POST"])
    @login_required
    def api_contacts_make_primary(contact_id):
        contact = Contact.query.filter_by(
            id=contact_id, user_id=current_user.id).first_or_404()
        Contact.query.filter_by(user_id=current_user.id).update({"is_primary": False})
        contact.is_primary = True
        db.session.commit()
        return jsonify({"success": True, "contact": contact.to_dict()})

    @app.route("/api/contacts/<int:contact_id>", methods=["DELETE"])
    @login_required
    def api_contacts_delete(contact_id):
        contact = Contact.query.filter_by(
            id=contact_id, user_id=current_user.id).first_or_404()
        was_primary = contact.is_primary
        name = contact.name
        db.session.delete(contact)
        db.session.commit()
        if was_primary:
            next_c = Contact.query.filter_by(user_id=current_user.id).first()
            if next_c:
                next_c.is_primary = True
                db.session.commit()
        return jsonify({"success": True, "deleted_name": name})

    # ------------------------------------------------------------------
    # API: Diet
    # ------------------------------------------------------------------
    @app.route("/api/diet/today")
    @login_required
    def api_diet_today():
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        plan = MealPlan.query.filter_by(
            user_id=current_user.id, plan_date=today_str).first()
        if not plan:
            engine = DietEngine()
            plan_dict = engine.generate_daily_plan(current_user, today_str)
            plan = MealPlan(user_id=current_user.id, plan_date=today_str,
                            plan_json=json.dumps(plan_dict))
            db.session.add(plan)
            db.session.commit()
        return jsonify({"plan": plan.get_plan_data(), "plan_id": plan.id,
                        "plan_date": plan.plan_date})

    @app.route("/api/diet/generate", methods=["POST"])
    @login_required
    def api_diet_generate():
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        engine = DietEngine()
        plan_dict = engine.generate_daily_plan(current_user, today_str)
        existing = MealPlan.query.filter_by(
            user_id=current_user.id, plan_date=today_str).first()
        if existing:
            existing.plan_json = json.dumps(plan_dict)
            existing.created_at = datetime.utcnow()
            plan = existing
        else:
            plan = MealPlan(user_id=current_user.id, plan_date=today_str,
                            plan_json=json.dumps(plan_dict))
            db.session.add(plan)
        db.session.commit()
        return jsonify({"success": True, "plan": plan.get_plan_data(),
                        "plan_id": plan.id, "plan_date": plan.plan_date})

    @app.route("/api/diet/history")
    @login_required
    def api_diet_history():
        plans = MealPlan.query.filter_by(user_id=current_user.id)\
            .order_by(MealPlan.created_at.desc()).all()
        return jsonify([
            {
                "id": p.id,
                "date": p.plan_date,
                "created_at": p.created_at.strftime("%d %B %Y at %I:%M %p"),
                "data": p.get_plan_data(),
            }
            for p in plans
        ])

    @app.route("/api/diet/plan/<int:plan_id>")
    @login_required
    def api_diet_plan(plan_id):
        plan = MealPlan.query.filter_by(
            id=plan_id, user_id=current_user.id).first_or_404()
        return jsonify({"plan": plan.get_plan_data(), "plan_id": plan.id,
                        "plan_date": plan.plan_date})

    # ------------------------------------------------------------------
    # API: Profile
    # ------------------------------------------------------------------
    @app.route("/api/profile")
    @login_required
    def api_profile_get():
        profile   = current_user.diet_profile
        reminders = current_user.reminder_settings
        allergies = [a.name for a in current_user.allergies]
        return jsonify({
            "name": current_user.name,
            "age": current_user.age,
            "email": current_user.email,
            "diet_type": profile.diet_type if profile else "veg",
            "allergies": ", ".join(allergies),
            "dislikes": profile.dislikes if profile else "",
            "restrictions": profile.restrictions if profile else "",
            "conditions_note": profile.conditions_note if profile else "",
            "clinician_note": profile.clinician_note if profile else "",
            "water_enabled": reminders.water_enabled if reminders else True,
            "water_interval_min": reminders.water_interval_min if reminders else 60,
            "meals_enabled": reminders.meals_enabled if reminders else True,
        })

    @app.route("/api/profile", methods=["POST"])
    @login_required
    def api_profile_save():
        data = request.get_json(silent=True) or {}
        errors = {}

        name = (data.get("name") or "").strip()
        if len(name) < 2:
            errors["name"] = "Name must be at least 2 characters."

        try:
            age = int(data.get("age"))
            if age < 50 or age > 120:
                errors["age"] = "Age must be between 50 and 120."
        except (TypeError, ValueError):
            errors["age"] = "Please enter a valid age."

        if errors:
            return jsonify({"success": False, "errors": errors}), 400

        current_user.name = name
        current_user.age  = age

        profile = current_user.diet_profile
        if not profile:
            profile = DietProfile(user_id=current_user.id)
            db.session.add(profile)

        profile.diet_type      = data.get("diet_type", "veg")
        profile.dislikes       = (data.get("dislikes") or "").strip()
        profile.restrictions   = (data.get("restrictions") or "").strip()
        profile.conditions_note= (data.get("conditions_note") or "").strip()
        profile.clinician_note = (data.get("clinician_note") or "").strip()

        Allergy.query.filter_by(user_id=current_user.id).delete()
        raw_allergies = data.get("allergies") or ""
        for item in {a.strip().lower() for a in raw_allergies.split(",") if a.strip()}:
            db.session.add(Allergy(user_id=current_user.id, name=item))

        reminders = current_user.reminder_settings
        if not reminders:
            reminders = ReminderSetting(user_id=current_user.id)
            db.session.add(reminders)

        reminders.water_enabled     = bool(data.get("water_enabled", True))
        reminders.water_interval_min= int(data.get("water_interval_min", 60))
        reminders.meals_enabled     = bool(data.get("meals_enabled", True))

        db.session.commit()
        return jsonify({"success": True})

    # ------------------------------------------------------------------
    # DB init
    # ------------------------------------------------------------------
    with app.app_context():
        db.create_all()

    return app


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_contact(data):
    errors = {}
    name = (data.get("name") or "").strip()
    if len(name) < 2:
        errors["name"] = "Name must be at least 2 characters."

    phone = re.sub(r"[\s\-\(\)]", "", (data.get("phone") or "").strip())
    if not re.match(r"^\+?[0-9]{10,15}$", phone):
        errors["phone"] = "Please enter a valid phone number (10–15 digits, e.g. +91 98765 43210)."

    tg = (data.get("telegram_chat_id") or "").strip()
    if tg and not re.match(r"^-?[0-9]{5,20}$", tg):
        errors["telegram_chat_id"] = "Telegram Chat ID must be numeric (e.g. 123456789)."

    return errors


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    application = create_app()
    print("=" * 65)
    print("  Starting ElderSOS SPA — http://127.0.0.1:5000")
    print("=" * 65)
    application.run(host="0.0.0.0", port=5000, debug=False)
