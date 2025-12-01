"""
Email Notification Service using Brevo (SendinBlue) API
"""
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class EmailService:
    """Brevo (formerly SendinBlue) email service"""
    
    def __init__(self, api_key: str, from_email: str, to_email: str):
        """
        Initialize email service
        
        Args:
            api_key: Brevo API key
            from_email: Sender email address
            to_email: Recipient email address
        """
        self.api_key = api_key
        self.from_email = from_email
        self.to_email = to_email
        self.api_url = "https://api.brevo.com/v3/smtp/email"
        
        self.enabled = bool(api_key and from_email and to_email)
        
        if self.enabled:
            logger.info(f"Email service enabled: {from_email} -> {to_email}")
        else:
            logger.warning("Email service disabled (missing configuration)")
    
    def send_alert(self, subject: str, body: str) -> bool:
        """
        Send email alert
        
        Args:
            subject: Email subject
            body: Email body (plain text)
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning("Email service not configured")
            return False
        
        try:
            headers = {
                'accept': 'application/json',
                'api-key': self.api_key,
                'content-type': 'application/json'
            }
            
            payload = {
                'sender': {
                    'name': 'AnLex Guard',
                    'email': self.from_email
                },
                'to': [
                    {'email': self.to_email}
                ],
                'subject': subject,
                'textContent': body
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 201:
                logger.info(f"Email sent successfully: {subject}")
                return True
            else:
                logger.error(f"Email send failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Email send error: {e}", exc_info=True)
            return False