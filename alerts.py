from datetime import datetime
from typing import Optional, Dict, Any
from flask import current_app
from models import db, Alert, AlertDelivery, Contact, User
from services.providers.base import BaseAlertProvider
from services.providers.console import ConsoleAlertProvider
from services.providers.telegram import TelegramAlertProvider
from services.providers.twilio import TwilioAlertProvider

def get_provider(provider_name: str) -> BaseAlertProvider:
    name = (provider_name or "").lower().strip()
    if name == "telegram":
        return TelegramAlertProvider()
    elif name == "twilio":
        return TwilioAlertProvider()
    else:
        return ConsoleAlertProvider()

def build_alert_message(user: User, alert: Alert, is_test: bool = False) -> str:
    lines = []
    if is_test:
        lines.append("🧪 [TEST ALERT - NO EMERGENCY / DEMO ONLY]")
        lines.append("------------------------------------------")
    else:
        lines.append("🚨 ‼️ EMERGENCY SOS ALERT - ELDERSOS ‼️ 🚨")
        lines.append("------------------------------------------")

    lines.append(f"👤 Senior Citizen: {user.name}")
    if user.age:
        lines.append(f"🎂 Age: {user.age} years")

    lines.append("⚠️ Message: Emergency assistance has been triggered from the ElderSOS application!")

    # Location Information
    if alert.lat is not None and alert.lng is not None:
        lines.append(f"📍 GPS Location (Exact Pin):")
        lines.append(f"https://www.google.com/maps?q={alert.lat},{alert.lng}")
    else:
        lines.append(f"📍 GPS Status: Location unavailable ({alert.location_status})")

    primary_contact = user.get_primary_contact()
    if primary_contact:
        lines.append(f"📞 Primary Contact: {primary_contact.name} ({primary_contact.phone})")

    lines.append(f"🚑 National Emergency Services in India: Dial 112")
    lines.append(f"⏰ Timestamp: {alert.created_at.strftime('%d-%b-%Y %I:%M:%S %p UTC')}")
    
    return "\n".join(lines)


def dispatch_sos_alert(
    user: User,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    location_status: str = "unavailable",
    message_custom: Optional[str] = None
) -> Dict[str, Any]:
    """
    Core SOS Dispatcher:
    - Enforces TEST mode when ALERT_MODE=test (using Console provider, labelled TEST in DB & UI)
    - In LIVE mode, verifies provider configuration honestly.
    - NEVER records 'sent' unless verified by the provider.
    - Records every delivery attempt in alert_deliveries table.
    """
    mode = current_app.config.get("ALERT_MODE", "test").lower().strip()
    configured_provider_name = current_app.config.get("ALERT_PROVIDER", "console").lower().strip()
    
    # In test mode, always route to console provider
    active_provider_name = "console" if mode == "test" else configured_provider_name
    provider = get_provider(active_provider_name)
    
    contacts = Contact.query.filter_by(user_id=user.id).order_by(Contact.is_primary.desc(), Contact.name.asc()).all()

    # Create the Alert record
    alert = Alert(
        user_id=user.id,
        created_at=datetime.utcnow(),
        message=message_custom or "Emergency Assistance Requested!",
        lat=lat,
        lng=lng,
        location_status=location_status,
        mode=mode,
        overall_status="pending"
    )
    db.session.add(alert)
    db.session.flush()  # Obtain alert.id

    # Fail fast if user has no contacts configured
    if not contacts:
        alert.overall_status = "failed"
        db.session.commit()
        return {
            "success": False,
            "alert_id": alert.id,
            "mode": mode,
            "overall_status": "failed",
            "error_summary": "No emergency contacts registered in your profile. Please add at least one family member or caregiver.",
            "deliveries": [],
            "primary_contact": None,
            "emergency_phone": "112"
        }

    # If live mode, check if provider is configured
    is_conf, unconf_reason = provider.is_configured()
    if mode == "live" and not is_conf:
        # Honest failure: Provider is not configured
        deliveries_summary = []
        for contact in contacts:
            delivery = AlertDelivery(
                alert_id=alert.id,
                contact_id=contact.id,
                provider=provider.name,
                status="failed",
                provider_ref=None,
                error=f"Provider not configured: {unconf_reason}"
            )
            db.session.add(delivery)
            deliveries_summary.append({
                "contact_id": contact.id,
                "contact_name": contact.name,
                "phone": contact.phone,
                "provider": provider.name,
                "status": "failed",
                "error": f"Provider not configured: {unconf_reason}"
            })
        
        alert.overall_status = "failed"
        db.session.commit()

        return {
            "success": False,
            "alert_id": alert.id,
            "mode": mode,
            "overall_status": "failed",
            "error_summary": f"Alert provider '{provider.name}' is not configured. {unconf_reason}",
            "deliveries": deliveries_summary,
            "primary_contact": user.get_primary_contact().to_dict() if user.get_primary_contact() else None,
            "emergency_phone": "112"
        }

    # Compose final message body
    text_message = build_alert_message(user, alert, is_test=(mode == "test"))

    # Send alert to each registered contact
    success_count = 0
    failure_count = 0
    deliveries_summary = []

    for contact in contacts:
        result = provider.send_alert(contact, alert, user, text_message)
        status_str = "sent" if result.success else "failed"

        delivery = AlertDelivery(
            alert_id=alert.id,
            contact_id=contact.id,
            provider=result.provider_name,
            status=status_str,
            provider_ref=result.provider_ref,
            error=result.error
        )
        db.session.add(delivery)

        deliveries_summary.append({
            "contact_id": contact.id,
            "contact_name": contact.name,
            "phone": contact.phone,
            "provider": result.provider_name,
            "status": status_str,
            "error": result.error,
            "provider_ref": result.provider_ref
        })

        if result.success:
            success_count += 1
        else:
            failure_count += 1

    # Determine overall status honestly
    if failure_count == 0:
        alert.overall_status = "sent"
    elif success_count > 0:
        alert.overall_status = "partial"
    else:
        alert.overall_status = "failed"

    db.session.commit()

    return {
        "success": (alert.overall_status in ("sent", "partial")),
        "alert_id": alert.id,
        "mode": mode,
        "overall_status": alert.overall_status,
        "maps_link": alert.get_maps_link(),
        "location_status": alert.location_status,
        "created_at": alert.created_at.strftime("%I:%M:%S %p, %d %b %Y"),
        "deliveries": deliveries_summary,
        "primary_contact": user.get_primary_contact().to_dict() if user.get_primary_contact() else None,
        "emergency_phone": "112"
    }
