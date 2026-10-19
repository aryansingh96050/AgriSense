import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger("agrisense.notifier")

# Simulated in-memory inbox for the farmer's smartphone demo
SIMULATED_PHONE_INBOX: List[Dict[str, Any]] = []

class NotifierService:
    def __init__(self):
        # Twilio credentials (optional)
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.twilio_from_sms = os.getenv("TWILIO_FROM_SMS", "")
        self.twilio_from_wa = os.getenv("TWILIO_FROM_WHATSAPP", "whatsapp:+14155238886")
        
        # Meta WhatsApp Cloud API credentials (optional)
        self.wa_cloud_token = os.getenv("WHATSAPP_CLOUD_TOKEN", "")
        self.wa_phone_id = os.getenv("WHATSAPP_PHONE_ID", "")
        
        # Fast2SMS (Indian SMS Gateway - optional)
        self.fast2sms_api_key = os.getenv("FAST2SMS_API_KEY", "")

    def send_sms(self, phone: str, text: str) -> Dict[str, Any]:
        """Dispatches an SMS alert via configured provider or simulated queue"""
        logger.info(f"[SMS Dispatch] To: {phone} | Text: {text}")
        status = "SIMULATED"
        details = "Stored in local inbox demo"

        # 1. Twilio SMS
        if self.twilio_sid and self.twilio_token and self.twilio_from_sms:
            try:
                url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_sid}/Messages.json"
                resp = requests.post(
                    url,
                    data={"To": phone, "From": self.twilio_from_sms, "Body": text},
                    auth=(self.twilio_sid, self.twilio_token),
                    timeout=5
                )
                if resp.status_code in (200, 201):
                    status = "DELIVERED_TWILIO"
                    details = resp.json().get("sid", "Twilio OK")
            except Exception as e:
                logger.error(f"Twilio SMS error: {e}")
                details = f"Twilio Error: {str(e)}"

        # 2. Fast2SMS (India domestic SMS)
        elif self.fast2sms_api_key:
            try:
                clean_phone = phone.replace("+91", "").strip()
                url = "https://www.fast2sms.com/dev/bulkV2"
                resp = requests.post(
                    url,
                    headers={"authorization": self.fast2sms_api_key},
                    data={"route": "v3", "sender_id": "TXTIND", "message": text, "language": "unicode", "numbers": clean_phone},
                    timeout=5
                )
                if resp.status_code == 200:
                    status = "DELIVERED_FAST2SMS"
                    details = "Fast2SMS OK"
            except Exception as e:
                logger.error(f"Fast2SMS error: {e}")

        # Always save to simulated inbox for immediate UI inspection
        inbox_entry = {
            "id": len(SIMULATED_PHONE_INBOX) + 1,
            "channel": "SMS",
            "sender": "AgriSense-Gov",
            "phone": phone,
            "message": text,
            "timestamp": datetime.now().strftime("%I:%M %p, %d %b"),
            "status": status,
            "details": details
        }
        SIMULATED_PHONE_INBOX.insert(0, inbox_entry)
        if len(SIMULATED_PHONE_INBOX) > 50:
            SIMULATED_PHONE_INBOX.pop()

        return inbox_entry

    def send_whatsapp(self, phone: str, text: str) -> Dict[str, Any]:
        """Dispatches a WhatsApp alert via Cloud API, Twilio or simulated queue"""
        logger.info(f"[WhatsApp Dispatch] To: {phone} | Text:\n{text}")
        status = "SIMULATED"
        details = "Stored in local inbox demo"

        # 1. WhatsApp Cloud API (Meta Graph API)
        if self.wa_cloud_token and self.wa_phone_id:
            try:
                clean_phone = phone.replace("+", "").strip()
                url = f"https://graph.facebook.com/v19.0/{self.wa_phone_id}/messages"
                headers = {
                    "Authorization": f"Bearer {self.wa_cloud_token}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "messaging_product": "whatsapp",
                    "to": clean_phone,
                    "type": "text",
                    "text": {"body": text}
                }
                resp = requests.post(url, json=payload, headers=headers, timeout=5)
                if resp.status_code == 200:
                    status = "DELIVERED_WHATSAPP_CLOUD"
                    details = "Meta API OK"
            except Exception as e:
                logger.error(f"WhatsApp Cloud API error: {e}")
                details = f"WA Cloud Error: {str(e)}"

        # 2. Twilio WhatsApp
        elif self.twilio_sid and self.twilio_token:
            try:
                url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_sid}/Messages.json"
                to_wa = phone if phone.startswith("whatsapp:") else f"whatsapp:{phone}"
                resp = requests.post(
                    url,
                    data={"To": to_wa, "From": self.twilio_from_wa, "Body": text},
                    auth=(self.twilio_sid, self.twilio_token),
                    timeout=5
                )
                if resp.status_code in (200, 201):
                    status = "DELIVERED_TWILIO_WA"
                    details = resp.json().get("sid", "Twilio WA OK")
            except Exception as e:
                logger.error(f"Twilio WhatsApp error: {e}")

        # Always record in simulated phone inbox
        inbox_entry = {
            "id": len(SIMULATED_PHONE_INBOX) + 1,
            "channel": "WHATSAPP",
            "sender": "AgriSense Advisor 🌱",
            "phone": phone,
            "message": text,
            "timestamp": datetime.now().strftime("%I:%M %p, %d %b"),
            "status": status,
            "details": details
        }
        SIMULATED_PHONE_INBOX.insert(0, inbox_entry)
        if len(SIMULATED_PHONE_INBOX) > 50:
            SIMULATED_PHONE_INBOX.pop()

        return inbox_entry

    def get_simulated_inbox(self) -> List[Dict[str, Any]]:
        return SIMULATED_PHONE_INBOX

notifier = NotifierService()
