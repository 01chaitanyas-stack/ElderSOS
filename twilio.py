import requests
from typing import Optional
from flask import current_app
from services.providers.base import BaseAlertProvider, ProviderResult

class TwilioAlertProvider(BaseAlertProvider):
    def __init__(self, account_sid: Optional[str] = None, auth_token: Optional[str] = None, from_phone: Optional[str] = None):
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._from_phone = from_phone

    @property
    def account_sid(self) -> str:
        if self._account_sid:
            return self._account_sid
        try:
            return current_app.config.get("TWILIO_ACCOUNT_SID", "").strip()
        except RuntimeError:
            return ""

    @property
    def auth_token(self) -> str:
        if self._auth_token:
            return self._auth_token
        try:
            return current_app.config.get("TWILIO_AUTH_TOKEN", "").strip()
        except RuntimeError:
            return ""

    @property
    def from_phone(self) -> str:
        if self._from_phone:
            return self._from_phone
        try:
            return current_app.config.get("TWILIO_PHONE_NUMBER", "").strip()
        except RuntimeError:
            return ""

    @property
    def name(self) -> str:
        return "twilio"

    def is_configured(self) -> tuple[bool, Optional[str]]:
        if not self.account_sid or not self.auth_token or not self.from_phone:
            missing = []
            if not self.account_sid: missing.append("TWILIO_ACCOUNT_SID")
            if not self.auth_token: missing.append("TWILIO_AUTH_TOKEN")
            if not self.from_phone: missing.append("TWILIO_PHONE_NUMBER")
            return False, f"Twilio SMS is not fully configured. Missing in .env: {', '.join(missing)}"
        return True, None

    def send_alert(self, contact, alert, user, text_message: str) -> ProviderResult:
        configured, reason = self.is_configured()
        if not configured:
            return ProviderResult(
                success=False,
                provider_name=self.name,
                provider_ref=None,
                error=reason
            )

        if not contact.phone:
            return ProviderResult(
                success=False,
                provider_name=self.name,
                provider_ref=None,
                error=f"Contact {contact.name} has no valid phone number recorded."
            )

        endpoint = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = {
            "To": contact.phone,
            "From": self.from_phone,
            "Body": text_message
        }

        try:
            response = requests.post(
                endpoint,
                data=data,
                auth=(self.account_sid, self.auth_token),
                timeout=10
            )
            res_json = response.json()
            if response.status_code in (200, 201) and "sid" in res_json:
                return ProviderResult(
                    success=True,
                    provider_name=self.name,
                    provider_ref=res_json["sid"],
                    error=None
                )
            else:
                err_msg = res_json.get("message", f"HTTP {response.status_code}")
                return ProviderResult(
                    success=False,
                    provider_name=self.name,
                    provider_ref=None,
                    error=f"Twilio API Error: {err_msg}"
                )
        except requests.exceptions.Timeout:
            return ProviderResult(
                success=False,
                provider_name=self.name,
                provider_ref=None,
                error="Twilio API request timed out."
            )
        except requests.exceptions.RequestException as e:
            return ProviderResult(
                success=False,
                provider_name=self.name,
                provider_ref=None,
                error=f"Network error contacting Twilio: {str(e)}"
            )
