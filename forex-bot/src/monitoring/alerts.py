import logging
import requests
from typing import Dict, Any

logger = logging.getLogger("trading.alerts")

class AlertManager:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.telegram_token = config.get("telegram_token")
        self.chat_id = config.get("telegram_chat_id")

    def send_alert(self, message: str):
        logger.info(f"ALERT: {message}")
        # Telegram
        if self.telegram_token and self.chat_id:
            try:
                url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
                data = {"chat_id": self.chat_id, "text": message}
                resp = requests.post(url, json=data, timeout=5)
                resp.raise_for_status()
            except Exception as e:
                logger.error(f"Error sending Telegram alert: {e}")

        # Email placeholder
        self.send_email("Forex Bot Alert", message)

    def send_email(self, subject: str, body: str):
        """
        Placeholder for email alerts (e.g. via AWS SES or SMTP).
        """
        email_to = self.config.get("email_to")
        if email_to:
            logger.info(f"Email would be sent to {email_to}: {subject}")

    def notify_flatten(self, reason: str, pnl: float):
        msg = f"🔔 Cycle Flattened!\nReason: {reason}\nP&L: ${pnl:.2f}"
        self.send_alert(msg)

    def notify_hard_stop(self, drawdown: float):
        msg = f"🚨 CRITICAL: Hard Stop Hit!\nDrawdown: {drawdown:.2%}\nImmediate flatten initiated."
        self.send_alert(msg)

    def notify_connectivity_loss(self, adapter_name: str):
        msg = f"⚠️ WARNING: Connectivity loss on {adapter_name}!"
        self.send_alert(msg)
