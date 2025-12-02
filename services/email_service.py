"""
Email Notification Service using SMTP via Brevo (SendinBlue) Relay
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)

class EmailService:
    """SMTP email service via Brevo relay"""
    
    def __init__(self, smtp_host: str = None, smtp_port: int = None, 
                 smtp_user: str = None, smtp_pass: str = None,
                 from_email: str = None, to_email: str = None):
        """
        Initialize email service with SMTP configuration
        
        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_user: SMTP authentication username
            smtp_pass: SMTP authentication password
            from_email: Sender email address
            to_email: Recipient email address
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_pass = smtp_pass
        self.from_email = from_email
        self.to_email = to_email
        
        # Check if SMTP is configured
        self.enabled = bool(
            smtp_host and smtp_port and smtp_user and smtp_pass 
            and from_email and to_email
        )
        
        if self.enabled:
            logger.info(f"Email service enabled (SMTP): {from_email} -> {to_email}")
        else:
            logger.warning("Email service disabled (missing SMTP configuration)")
    
    def send_alert(self, subject: str, body: str) -> bool:
        """
        Send email alert via SMTP
        
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
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"AnLex Guard <{self.from_email}>"
            msg['To'] = self.to_email
            msg['Subject'] = subject
            
            # Attach body
            msg.attach(MIMEText(body, 'plain'))
            
            # Connect to SMTP server
            logger.debug(f"Connecting to SMTP server: {self.smtp_host}:{self.smtp_port}")
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.starttls()  # Enable TLS encryption
                server.login(self.smtp_user, self.smtp_pass)
                
                # Send email
                server.send_message(msg)
                
            logger.info(f"Email sent successfully via SMTP: {subject}")
            return True
                
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Email send error: {e}", exc_info=True)
            return False