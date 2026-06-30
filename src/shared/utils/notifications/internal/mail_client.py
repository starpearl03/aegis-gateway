import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

logger = logging.getLogger(__name__)


class MailClient:
    """Client for sending emails via SMTP with lazy loading configuration"""

    def __init__(self):
        """Initialize MailClient - config will be retrieved from Flask app context"""
        self._email_config = None
        self._initialized = False
        self.smtp_server = None

    @property
    def email_config(self):
        """Lazy load email config from Flask app context"""
        if self._email_config is None:
            if not current_app:
                raise RuntimeError("MailClient must be used within Flask application context")
            self._email_config = current_app.config['INTEGRATIONS']['EMAIL']
        return self._email_config

    def _connect_smtp(self) -> None:
        """Establish secure SMTP connection"""
        try:
            smtp_config = self.email_config.smtp
            smtp_host = str(smtp_config.host)
            smtp_port = int(smtp_config.port)

            logger.info(f"Connecting to SMTP server {smtp_host}:{smtp_port}")

            # Create SMTP connection based on TLS setting
            if smtp_config.use_tls:
                self.smtp_server = smtplib.SMTP(smtp_host, smtp_port)
                self.smtp_server.starttls()
            else:
                self.smtp_server = smtplib.SMTP_SSL(smtp_host, smtp_port)

            # Set a timeout for operations
            self.smtp_server.timeout = 10

            username = str(smtp_config.username)
            password = str(smtp_config.password)

            logger.info(f"Logging in as {username}")
            self.smtp_server.login(username, password)

            logger.info("SMTP connection established successfully")
        except Exception as e:
            logger.error(f"SMTP connection error: {e}")
            raise

    def send_email(
            self,
            subject: str,
            recipient: str,
            body: str,
            is_html: bool = True,
    ) -> bool:
        """
        Send email

        Args:
            subject: Email subject
            recipient: Recipient email address
            body: Email body content
            is_html: Whether the body content is HTML (default: True)

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            self._connect_smtp()

            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.email_config.from_name} <{self.email_config.from_email}>"
            msg['To'] = recipient

            # Attach body
            msg.attach(MIMEText(body, 'html' if is_html else 'plain'))

            logger.info(f"Sending email to {recipient}")
            self.smtp_server.sendmail(
                self.email_config.from_email,
                recipient,
                msg.as_string()
            )

            logger.info(f"Email sent successfully to {recipient}")
            return True

        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return False
        finally:
            if self.smtp_server:
                try:
                    self.smtp_server.quit()
                    logger.info("SMTP connection closed")
                except Exception as e:
                    logger.error(f"Error closing SMTP connection: {e}")