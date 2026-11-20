import json
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, MealPlan, DietProfile, Allergy
from services.diet_engine import DietEngine

diet_bp = Blueprint("diet", __name__, url_prefix="/diet")

@diet_bp.route("/")
@login_required
def index():
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    current_plan = MealPlan.query.filter_by(user_id=current_user.id, plan_date=today_str).first()
    
    # Auto-generate today's plan if none exists yet
    if not current_plan:
        engine = DietEngine()
        plan_dict = engine.generate_daily_plan(current_user, today_str)
        current_plan = MealPlan(
            user_id=current_user.id,
            plan_date=today_str,
            plan_json=json.dumps(plan_dict)
        )
        db.session.add(current_plan)
        db.session.commit()
        
    plan_data = current_plan.get_plan_data()
    return render_template("diet.html", plan=plan_data, plan_id=current_plan.id, plan_date=today_str)


@diet_bp.route("/generate", methods=["POST"])
@login_required
def generate():
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    engine = DietEngine()
    plan_dict = engine.generate_daily_plan(current_user, today_str)
    
    # Check if a plan already exists for today
    existing = MealPlan.query.filter_by(user_id=current_user.id, plan_date=today_str).first()
    if existing:
        existing.plan_json = json.dumps(plan_dict)
        existing.created_at = datetime.utcnow()
    else:
        new_plan = MealPlan(
            user_id=current_user.id,
            plan_date=today_str,
            plan_json=json.dumps(plan_dict)
        )
        db.session.add(new_plan)
        
    db.session.commit()
    flash("Fresh personalized daily meal plan successfully generated!", "success")
    return redirect(url_for("diet.index"))


@diet_bp.route("/history")
@login_required
def history():
    plans = MealPlan.query.filter_by(user_id=current_user.id).order_by(MealPlan.created_at.desc()).all()
    parsed_plans = []
    for p in plans:
        parsed_plans.append({
            "id": p.id,
            "date": p.plan_date,
            "created_at": p.created_at,
            "data": p.get_plan_data()
        })
    return render_template("diet_history.html", plans=parsed_plans)


@diet_bp.route("/plan/<int:plan_id>")
@login_required
def view_plan(plan_id):
    plan_record = MealPlan.query.filter_by(id=plan_id, user_id=current_user.id).first_or_404()
    plan_data = plan_record.get_plan_data()
    return render_template("diet.html", plan=plan_data, plan_id=plan_record.id, plan_date=plan_record.plan_date, is_historical=True)
