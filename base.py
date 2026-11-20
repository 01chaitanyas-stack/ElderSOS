from abc import ABC, abstractmethod
from typing import Optional

class ProviderResult:
    def __init__(self, success: bool, provider_name: str, provider_ref: Optional[str] = None, error: Optional[str] = None):
        self.success = success
        self.provider_name = provider_name
        self.provider_ref = provider_ref
        self.error = error

    def to_dict(self):
        return {
            "success": self.success,
            "provider": self.provider_name,
            "provider_ref": self.provider_ref,
            "error": self.error
        }

class BaseAlertProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique provider identifier (e.g. 'console', 'telegram', 'twilio')"""
        pass

    @abstractmethod
    def is_configured(self) -> tuple[bool, Optional[str]]:
        """Returns (is_configured, reason_if_not)"""
        pass

    @abstractmethod
    def send_alert(self, contact, alert, user, text_message: str) -> ProviderResult:
        """Sends emergency alert message to a single contact"""
        pass
