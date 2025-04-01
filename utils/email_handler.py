import os
import logging
import smtplib
from typing import Dict
from pathlib import Path
from dotenv import load_dotenv
from email.message import EmailMessage

logger = logging.getLogger(__name__)

# Get the project root directory and load .env.local file
project_root = Path(__file__).parent.parent
env_path = project_root / 'env' / '.env.local'
load_dotenv(dotenv_path=env_path)

class EmailHandler:
    def __init__(self):
        """Initialize email configuration from .env.local file"""
        # Load SMTP configuration with fallback values
        self.smtp_server = os.getenv("SMTP_SERVER", "live.smtp.mailtrap.io")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME", "api")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "your_password_here")
        self.sender_email = os.getenv("SENDER_EMAIL", "hello@demomailtrap.co")

        log_details = {
            'smtp_server': self.smtp_server,
            'smtp_port': self.smtp_port,
            'smtp_username': self.smtp_username,
            'smtp_password': '*' * len(self.smtp_password) if self.smtp_password else None,  # mask password
            'sender_email': self.sender_email
        }
        logger.info(f"Email configuration details: {log_details}")
        
        # Validate configuration
        self._validate_config()

    def _validate_config(self):
        """Validate that all required configuration is present"""
        required_vars = {
            "SMTP_SERVER": self.smtp_server,
            "SMTP_PORT": self.smtp_port,
            "SMTP_USERNAME": self.smtp_username,
            "SMTP_PASSWORD": self.smtp_password,
            "SENDER_EMAIL": self.sender_email
        }
        
        missing_vars = [var for var, value in required_vars.items() 
                       if not value or value == "your_password_here"]
        
        if missing_vars:
            logger.warning(f"Missing required email configuration: {', '.join(missing_vars)}")

    def send_email(self, recipient: str, subject: str, body: str) -> Dict[str, str]:
        """
        Sends an email using configured SMTP server
        Args:
            recipient: Recipient email address
            subject: Email subject
            body: Email body text
        Returns:
            Dict containing status and optional error message
        """
        msg = EmailMessage()
        msg["From"] = f"Payment Flow Analysis <{self.sender_email}>"
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(body)

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            return {"status": "success", "message": "Email sent successfully"}
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return {"status": "error", "message": str(e)} 