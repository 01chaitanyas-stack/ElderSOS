from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Length, Optional
from models import db, User, DietProfile, Allergy, ReminderSetting

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")

class ProfileForm(FlaskForm):
    # Personal Info
    name = StringField("Senior's Full Name", validators=[
        DataRequired(message="Name is required."),
        Length(min=2, max=100)
    ])
    age = IntegerField("Age (Years)", validators=[
        DataRequired(message="Age is required."),
        NumberRange(min=50, max=120, message="Please enter an age between 50 and 120.")
    ])

    # Dietary Preferences
    diet_type = SelectField("Dietary Preference", choices=[
        ("veg", "Vegetarian (Dairy allowed, No meat/fish/eggs)"),
        ("vegan", "Vegan (100% Plant-based, No dairy/meat/eggs)"),
        ("non-veg", "Non-Vegetarian (Eggs, Fish & Chicken allowed)")
    ], validators=[DataRequired()])
    
    allergies = StringField("Known Food Allergies (Comma-separated)", validators=[Optional()])
    dislikes = StringField("Disliked Foods or Ingredients (Comma-separated)", validators=[Optional()])
    restrictions = StringField("Dietary Restrictions (e.g. low-sodium, soft-food)", validators=[Optional()])
    
    # Clinical Health Notes
    conditions_note = TextAreaField("Diagnosed Medical Conditions (Optional)", validators=[Optional()])
    clinician_note = TextAreaField("Prescribed Doctor / Dietician Instructions (Optional)", validators=[Optional()])

    # Reminders
    water_enabled = BooleanField("Enable Hourly Hydration Reminders")
    water_interval_min = IntegerField("Water Reminder Interval (Minutes)", default=60, validators=[
        NumberRange(min=15, max=240, message="Interval should be between 15 and 240 minutes.")
    ])
    meals_enabled = BooleanField("Enable Daily Meal Timing Reminders")
    
    submit = SubmitField("Save Profile & Diet Settings")


@profile_bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    profile = current_user.diet_profile
    reminders = current_user.reminder_settings

    # If user doesn't have profile records yet, initialize them
    if not profile:
        profile = DietProfile(user_id=current_user.id, diet_type="veg")
        db.session.add(profile)
        db.session.commit()
    if not reminders:
        reminders = ReminderSetting(user_id=current_user.id)
        db.session.add(reminders)
        db.session.commit()

    form = ProfileForm()

    if request.method == "POST" and form.validate_on_submit():
        # Update user basics
        current_user.name = form.name.data.strip()
        current_user.age = form.age.data

        # Update Diet Profile
        profile.diet_type = form.diet_type.data
        profile.dislikes = form.dislikes.data.strip() if form.dislikes.data else ""
        profile.restrictions = form.restrictions.data.strip() if form.restrictions.data else ""
        profile.conditions_note = form.conditions_note.data.strip() if form.conditions_note.data else ""
        profile.clinician_note = form.clinician_note.data.strip() if form.clinician_note.data else ""

        # Update Allergies (parse comma-separated string)
        Allergy.query.filter_by(user_id=current_user.id).delete()
        if form.allergies.data:
            raw_allergies = [a.strip().lower() for a in form.allergies.data.split(",") if a.strip()]
            for item in set(raw_allergies):
                db.session.add(Allergy(user_id=current_user.id, name=item))

        # Update Reminders
        reminders.water_enabled = form.water_enabled.data
        reminders.water_interval_min = form.water_interval_min.data
        reminders.meals_enabled = form.meals_enabled.data

        db.session.commit()
        flash("Your profile, dietary restrictions, and reminder preferences have been updated!", "success")
        return redirect(url_for("profile.index"))

    elif request.method == "GET":
        # Prefill form fields
        form.name.data = current_user.name
        form.age.data = current_user.age
        form.diet_type.data = profile.diet_type
        form.dislikes.data = profile.dislikes
        form.restrictions.data = profile.restrictions
        form.conditions_note.data = profile.conditions_note
        form.clinician_note.data = profile.clinician_note
        
        # Current allergies as comma-separated
        current_allergies = [a.name for a in current_user.allergies]
        form.allergies.data = ", ".join(current_allergies)

        form.water_enabled.data = reminders.water_enabled
        form.water_interval_min.data = reminders.water_interval_min
        form.meals_enabled.data = reminders.meals_enabled

    return render_template("profile.html", form=form)
