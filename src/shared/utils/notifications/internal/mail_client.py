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
            self.smtp_server.timeout = 60

            username = str(smtp_config.username)
            password = str(smtp_config.password)

            logger.info(f"Logging in as {username}")
            self.smtp_server.login(username, password)

            logger.info("SMTP connection established successfully")
        except smtplib.SMTPAuthenticationError as e:
            error_msg = f"SMTP authentication failed for {smtp_config.username}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(f"SMTP Authentication Error: Check your email credentials in config.yaml - {str(e)}")
        except smtplib.SMTPConnectError as e:
            error_msg = f"Failed to connect to SMTP server {smtp_host}:{smtp_port}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(f"SMTP Connection Error: Cannot reach email server - {str(e)}")
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(f"SMTP Error: {str(e)}")
        except Exception as e:
            error_msg = f"Unexpected SMTP connection error: {str(e)}"
            logger.error(f"❌ {error_msg}")
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

            logger.info(f"✅ Email sent successfully to {recipient}")
            return True

        except smtplib.SMTPRecipientsRefused as e:
            error_msg = f"Recipient {recipient} was refused by the server: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(f"Invalid recipient email address: {recipient} - {str(e)}")
        except smtplib.SMTPSenderRefused as e:
            error_msg = f"Sender {self.email_config.from_email} was refused: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(f"Invalid sender email address - {str(e)}")
        except smtplib.SMTPDataError as e:
            error_msg = f"SMTP data error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            raise Exception(f"Email content rejected by server - {str(e)}")
        except Exception as e:
            error_msg = f"Failed to send email to {recipient}: {str(e)}"
            logger.error(f"❌ {error_msg}")
            # Re-raise the exception so it can be caught by NotificationService
            raise
        finally:
            if self.smtp_server:
                try:
                    self.smtp_server.quit()
                    logger.info("SMTP connection closed")
                except Exception as e:
                    logger.error(f"Error closing SMTP connection: {e}")