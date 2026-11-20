from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Alert, Contact, AlertDelivery, MealPlan
from services.alerts import dispatch_sos_alert
from datetime import datetime

sos_bp = Blueprint("sos", __name__)

@sos_bp.route("/")
def root():
    if current_user.is_authenticated:
        return redirect(url_for("sos.dashboard"))
    return redirect(url_for("auth.login"))

@sos_bp.route("/dashboard")
@login_required
def dashboard():
    primary_contact = current_user.get_primary_contact()
    contacts_count = Contact.query.filter_by(user_id=current_user.id).count()
    recent_alerts = Alert.query.filter_by(user_id=current_user.id).order_by(Alert.created_at.desc()).limit(3).all()
    
    # Retrieve today's meal plan if available
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    today_plan = MealPlan.query.filter_by(user_id=current_user.id, plan_date=today_str).first()
    
    return render_template(
        "dashboard.html",
        primary_contact=primary_contact,
        contacts_count=contacts_count,
        recent_alerts=recent_alerts,
        today_plan=today_plan
    )

@sos_bp.route("/sos")
@login_required
def sos_page():
    primary_contact = current_user.get_primary_contact()
    contacts = Contact.query.filter_by(user_id=current_user.id).all()
    return render_template(
        "sos.html",
        primary_contact=primary_contact,
        contacts=contacts
    )

@sos_bp.route("/sos/history")
@login_required
def history():
    alerts = Alert.query.filter_by(user_id=current_user.id).order_by(Alert.created_at.desc()).all()
    return render_template("history.html", alerts=alerts)

@sos_bp.route("/api/sos", methods=["POST"])
@login_required
def api_sos():
    """
    POST /api/sos
    Triggers emergency alert with optional geolocation.
    CSRF protected.
    """
    data = request.get_json(silent=True) or {}
    
    lat = data.get("lat")
    lng = data.get("lng")
    location_status = data.get("location_status", "unavailable")
    
    # Clean lat/lng if provided
    try:
        lat = float(lat) if lat is not None else None
        lng = float(lng) if lng is not None else None
    except (ValueError, TypeError):
        lat = None
        lng = None
        location_status = "unavailable"

    result = dispatch_sos_alert(
        user=current_user,
        lat=lat,
        lng=lng,
        location_status=location_status
    )
    
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code
