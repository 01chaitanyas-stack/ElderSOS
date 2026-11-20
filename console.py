import uuid
from datetime import datetime
from services.providers.base import BaseAlertProvider, ProviderResult

class ConsoleAlertProvider(BaseAlertProvider):
    @property
    def name(self) -> str:
        return "console"

    def is_configured(self) -> tuple[bool, str | None]:
        # Console provider is always ready for test/dev mode
        return True, None

    def send_alert(self, contact, alert, user, text_message: str) -> ProviderResult:
        ref_id = f"console-{uuid.uuid4().hex[:8]}"
        now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        print("\n" + "=" * 65)
        print(f"📢 [ELDER-SOS CONSOLE ALERT - TEST MODE] Timestamp: {now_str}")
        print(f"👉 Target Contact: {contact.name} ({contact.relationship}) | Phone: {contact.phone}")
        print(f"📍 GPS Status: {alert.location_status} | Lat: {alert.lat}, Lng: {alert.lng}")
        print(f"💬 Message Payload:\n{text_message}")
        print(f"🔖 Generated Ref: {ref_id}")
        print("=" * 65 + "\n")
        
        return ProviderResult(
            success=True,
            provider_name=self.name,
            provider_ref=ref_id,
            error=None
        )
