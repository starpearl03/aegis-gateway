import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from flask import current_app

logger = logging.getLogger(__name__)


class SMSClient:
    """Client for sending SMS messages using Twilio with lazy loading configuration"""

    def __init__(self):
        """Initialize SMSClient - config will be retrieved from Flask app context"""
        self._twilio_config = None
        self._client = None
        self._initialized = False

    @property
    def twilio_config(self):
        """Lazy load Twilio config from Flask app context"""
        if self._twilio_config is None:
            if not current_app:
                raise RuntimeError("SMSClient must be used within Flask application context")
            self._twilio_config = current_app.config['INTEGRATIONS']['TWILIO']
        return self._twilio_config

    @property
    def client(self):
        """Lazy initialize Twilio client"""
        if not self._initialized:
            try:
                account_sid = self.twilio_config.account_sid
                auth_token = self.twilio_config.auth_token

                if not all([account_sid, auth_token]):
                    logger.warning("⚠️ SMS configuration incomplete. SMS functionality disabled.")
                    self._client = None
                else:
                    self._client = Client(account_sid, auth_token)
                    logger.info("✅ Twilio client initialized successfully")

                self._initialized = True
            except Exception as e:
                logger.error(f"❌ Failed to initialize Twilio client: {str(e)}")
                self._client = None
                self._initialized = True

        return self._client

    @staticmethod
    def _get_twilio_error_details(error_code: int, error_msg: str, to_number: str, from_number: str) -> str:
        """Get detailed explanation for Twilio error codes"""
        error_details = {
            20003: f"Authentication failed. Check ACCOUNT_SID and AUTH_TOKEN",
            21211: f"Invalid phone number: {to_number}. Must include country code (+263xxxxxxxxx)",
            21408: f"From number {from_number} not active or not verified",
            21610: f"Unverified number: {to_number}. Trial accounts can only send to verified numbers",
            21614: f"Invalid From number: {from_number}. Check PHONE_NUMBER in config",
            21617: f"From number is not SMS-enabled",
            21606: f"From number not owned by account or not SMS-capable",
            20429: "Rate limit exceeded",
            21608: f"Unverified number: {to_number} (trial account)",
            21612: f"Cannot send SMS to landline: {to_number}",
        }
        return error_details.get(error_code, error_msg)

    def send_sms(self, to_number: str, message: str) -> tuple[bool, str | None]:
        """
        Send an SMS message

        Args:
            to_number: Recipient phone number (must include country code, e.g. +263xxxxxxxxx)
            message: SMS message content

        Returns:
            Tuple of (success: bool, message_sid: str | None)
        """
        if not self.client:
            error_msg = "Twilio client not initialized. Check ACCOUNT_SID and AUTH_TOKEN"
            logger.error(f"❌ {error_msg}")
            raise Exception(error_msg)

        original_number = to_number
        try:
            # Format the phone number if needed
            if not to_number.startswith('+'):
                to_number = f"+263{to_number.lstrip('0')}"
                logger.info(f"📱 Formatted: {original_number} → {to_number}")

            logger.info(f"📤 Sending SMS to {to_number}")

            # Create and send the message
            twilio_message = self.client.messages.create(
                body=message,
                from_=self.twilio_config.phone_number,
                to=to_number
            )

            logger.info(f"✅ SMS sent | SID: {twilio_message.sid} | Status: {twilio_message.status}")
            return True, twilio_message.sid

        except TwilioRestException as e:
            error_code = e.code
            error_msg = e.msg
            detailed_error = self._get_twilio_error_details(
                error_code,
                error_msg,
                to_number,
                self.twilio_config.phone_number
            )

            logger.error(
                f"❌ Twilio error [{error_code}] sending to {to_number}\n"
                f"   Message: {error_msg}\n"
                f"   Details: {detailed_error}"
            )

            raise Exception(f"Twilio Error [{error_code}]: {detailed_error}")

        except Exception as e:
            logger.error(f"❌ Unexpected SMS error to {to_number}: {str(e)}")
            raise

    def send_found_notification(self, to_number: str, missing_person_name: str) -> bool:
        """
        Send a notification SMS when a missing person is found

        Args:
            to_number: Recipient phone number
            missing_person_name: Name of the missing person

        Returns:
            bool: True if SMS sent successfully, False otherwise
        """
        message = (
            f"POLICE NOTIFICATION: {missing_person_name} has been located. "
            f"Please contact the police department at (040) 2717860 for more information."
        )
        success, _ = self.send_sms(to_number, message)
        return success