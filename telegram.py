import requests
from typing import Optional
from flask import current_app
from services.providers.base import BaseAlertProvider, ProviderResult

class TelegramAlertProvider(BaseAlertProvider):
    def __init__(self, bot_token: Optional[str] = None):
        self._bot_token = bot_token

    @property
    def bot_token(self) -> str:
        if self._bot_token:
            return self._bot_token
        try:
            return current_app.config.get("TELEGRAM_BOT_TOKEN", "").strip()
        except RuntimeError:
            return ""

    @property
    def name(self) -> str:
        return "telegram"

    def is_configured(self) -> tuple[bool, Optional[str]]:
        token = self.bot_token
        if not token:
            return False, "TELEGRAM_BOT_TOKEN is not set in environment or .env. Please generate one via @BotFather."
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

        chat_id = contact.telegram_chat_id
        if not chat_id:
            return ProviderResult(
                success=False,
                provider_name=self.name,
                provider_ref=None,
                error=f"No Telegram Chat ID found for {contact.name}. Add Chat ID in Contacts settings."
            )

        api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text_message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        }

        try:
            response = requests.post(api_url, json=payload, timeout=8)
            resp_data = response.json()
            
            if response.status_code == 200 and resp_data.get("ok"):
                message_id = str(resp_data.get("result", {}).get("message_id"))
                return ProviderResult(
                    success=True,
                    provider_name=self.name,
                    provider_ref=f"tg-{message_id}",
                    error=None
                )
            else:
                desc = resp_data.get("description", f"HTTP {response.status_code}")
                return ProviderResult(
                    success=False,
                    provider_name=self.name,
                    provider_ref=None,
                    error=f"Telegram Error: {desc}"
                )
        except requests.exceptions.Timeout:
            return ProviderResult(
                success=False,
                provider_name=self.name,
                provider_ref=None,
                error="Telegram API timed out after 8 seconds. Please check internet connection."
            )
        except requests.exceptions.RequestException as e:
            return ProviderResult(
                success=False,
                provider_name=self.name,
                provider_ref=None,
                error=f"Network error contacting Telegram: {str(e)}"
            )
