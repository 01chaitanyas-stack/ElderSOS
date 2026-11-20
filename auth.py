from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange, ValidationError
from models import db, User, DietProfile, ReminderSetting

auth_bp = Blueprint("auth", __name__)

class RegisterForm(FlaskForm):
    name = StringField("Full Name", validators=[
        DataRequired(message="Please enter your full name."),
        Length(min=2, max=100, message="Name must be between 2 and 100 characters.")
    ])
    email = StringField("Email Address", validators=[
        DataRequired(message="Please enter a valid email address."),
        Email(message="Invalid email address format.")
    ])
    age = IntegerField("Age (Years)", validators=[
        DataRequired(message="Please provide your age."),
        NumberRange(min=50, max=120, message="ElderSOS is designed for seniors aged 50 and above.")
    ])
    password = PasswordField("Password", validators=[
        DataRequired(message="Please choose a password."),
        Length(min=6, message="Password must be at least 6 characters.")
    ])
    confirm_password = PasswordField("Confirm Password", validators=[
        DataRequired(message="Please re-type your password."),
        EqualTo("password", message="Passwords do not match.")
    ])
    submit = SubmitField("Create Senior Account")

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data.lower().strip()).first()
        if user:
            raise ValidationError("An account with this email is already registered. Please log in.")


class LoginForm(FlaskForm):
    email = StringField("Email Address", validators=[
        DataRequired(message="Please enter your email."),
        Email(message="Invalid email format.")
    ])
    password = PasswordField("Password", validators=[
        DataRequired(message="Please enter your password.")
    ])
    remember = BooleanField("Keep me logged in on this device")
    submit = SubmitField("Log In to ElderSOS")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("sos.dashboard"))
        
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
            age=form.age.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()  # to obtain user.id
        
        # Initialize default diet profile and reminder settings for this user
        profile = DietProfile(
            user_id=user.id,
            diet_type="veg",
            dislikes="",
            restrictions="low-sodium",
            conditions_note="",
            clinician_note=""
        )
        reminders = ReminderSetting(
            user_id=user.id,
            meals_enabled=True,
            water_enabled=True,
            water_interval_min=60
        )
        db.session.add(profile)
        db.session.add(reminders)
        db.session.commit()
        
        login_user(user)
        flash(f"Welcome to ElderSOS, {user.name}! Your account is ready.", "success")
        return redirect(url_for("sos.dashboard"))
        
    return render_template("register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("sos.dashboard"))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash(f"Welcome back, {user.name}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("sos.dashboard"))
        else:
            flash("Incorrect email or password. Please verify your details.", "danger")
            
    return render_template("login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been safely logged out.", "info")
    return redirect(url_for("auth.login"))
