import re
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, ValidationError
from models import db, Contact

contacts_bp = Blueprint("contacts", __name__, url_prefix="/contacts")

def validate_phone_number(form, field):
    raw_val = field.data.strip() if field.data else ""
    cleaned = re.sub(r"[\s\-\(\)]", "", raw_val)
    if not re.match(r"^\+?[0-9]{10,15}$", cleaned):
        raise ValidationError("Please enter a valid phone number (at least 10 digits, e.g. +91 98765 43210).")

def validate_telegram_id(form, field):
    if field.data:
        val = field.data.strip()
        if not re.match(r"^-?[0-9]{5,20}$", val):
            raise ValidationError("Telegram Chat ID should be numeric (e.g. 123456789). Use @userinfobot on Telegram to find it.")

class ContactForm(FlaskForm):
    name = StringField("Contact Name", validators=[
        DataRequired(message="Contact name is required."),
        Length(min=2, max=100, message="Name must be between 2 and 100 characters.")
    ])
    relationship = SelectField("Relationship to Senior", choices=[
        ("Son", "Son"),
        ("Daughter", "Daughter"),
        ("Spouse", "Spouse / Partner"),
        ("Caregiver", "Caregiver / Nurse"),
        ("Doctor", "Doctor / Healthcare Provider"),
        ("Neighbor", "Neighbor"),
        ("Friend", "Friend / Relative"),
        ("Other", "Other")
    ], validators=[DataRequired(message="Please select a relationship.")])
    
    phone = StringField("Phone Number", validators=[
        DataRequired(message="Phone number is required for direct emergency calls."),
        validate_phone_number
    ])
    
    telegram_chat_id = StringField("Telegram Chat ID (Optional)", validators=[
        Optional(),
        validate_telegram_id
    ])
    
    is_primary = BooleanField("Mark as Primary Emergency Contact")
    submit = SubmitField("Save Contact")


@contacts_bp.route("/", methods=["GET"])
@login_required
def index():
    contacts = Contact.query.filter_by(user_id=current_user.id).order_by(Contact.is_primary.desc(), Contact.name.asc()).all()
    form = ContactForm()
    return render_template("contacts.html", contacts=contacts, form=form, edit_contact=None)


@contacts_bp.route("/add", methods=["POST"])
@login_required
def add():
    form = ContactForm()
    if form.validate_on_submit():
        user_contacts = Contact.query.filter_by(user_id=current_user.id).all()
        is_first = (len(user_contacts) == 0)
        make_primary = form.is_primary.data or is_first
        
        if make_primary:
            Contact.query.filter_by(user_id=current_user.id, is_primary=True).update({"is_primary": False})
            
        contact = Contact(
            user_id=current_user.id,
            name=form.name.data.strip(),
            relationship=form.relationship.data,
            phone=form.phone.data.strip(),
            telegram_chat_id=form.telegram_chat_id.data.strip() if form.telegram_chat_id.data else None,
            is_primary=make_primary
        )
        db.session.add(contact)
        db.session.commit()
        flash(f"Contact '{contact.name}' successfully added.", "success")
        return redirect(url_for("contacts.index"))
        
    contacts = Contact.query.filter_by(user_id=current_user.id).order_by(Contact.is_primary.desc(), Contact.name.asc()).all()
    flash("Please correct the errors in the contact form below.", "danger")
    return render_template("contacts.html", contacts=contacts, form=form, edit_contact=None)


@contacts_bp.route("/<int:contact_id>/edit", methods=["GET", "POST"])
@login_required
def edit(contact_id):
    contact = Contact.query.filter_by(id=contact_id, user_id=current_user.id).first_or_404()
    form = ContactForm(obj=contact)
    
    if request.method == "POST" and form.validate_on_submit():
        if form.is_primary.data and not contact.is_primary:
            Contact.query.filter_by(user_id=current_user.id, is_primary=True).update({"is_primary": False})
            
        contact.name = form.name.data.strip()
        contact.relationship = form.relationship.data
        contact.phone = form.phone.data.strip()
        contact.telegram_chat_id = form.telegram_chat_id.data.strip() if form.telegram_chat_id.data else None
        contact.is_primary = form.is_primary.data
        
        db.session.commit()
        flash(f"Updated details for '{contact.name}'.", "success")
        return redirect(url_for("contacts.index"))
        
    contacts = Contact.query.filter_by(user_id=current_user.id).order_by(Contact.is_primary.desc(), Contact.name.asc()).all()
    return render_template("contacts.html", contacts=contacts, form=form, edit_contact=contact)


@contacts_bp.route("/<int:contact_id>/make-primary", methods=["POST"])
@login_required
def make_primary(contact_id):
    contact = Contact.query.filter_by(id=contact_id, user_id=current_user.id).first_or_404()
    Contact.query.filter_by(user_id=current_user.id).update({"is_primary": False})
    contact.is_primary = True
    db.session.commit()
    flash(f"'{contact.name}' is now your Primary Emergency Contact.", "success")
    return redirect(url_for("contacts.index"))


@contacts_bp.route("/<int:contact_id>/delete", methods=["POST"])
@login_required
def delete(contact_id):
    contact = Contact.query.filter_by(id=contact_id, user_id=current_user.id).first_or_404()
    was_primary = contact.is_primary
    db.session.delete(contact)
    db.session.commit()
    
    if was_primary:
        next_contact = Contact.query.filter_by(user_id=current_user.id).first()
        if next_contact:
            next_contact.is_primary = True
            db.session.commit()
            
    flash(f"Contact '{contact.name}' has been deleted.", "info")
    return redirect(url_for("contacts.index"))
