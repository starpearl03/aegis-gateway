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
                    logger.warning("SMS configuration incomplete. SMS functionality disabled.")
                    self._client = None
                else:
                    self._client = Client(account_sid, auth_token)
                    logger.info("Twilio client initialized successfully")

                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {str(e)}")
                self._client = None
                self._initialized = True

        return self._client

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
            logger.error("Twilio client not initialized. Cannot send SMS.")
            return False, None

        try:
            # Format the phone number if needed
            if not to_number.startswith('+'):
                # Assume Zimbabwe number if no country code
                to_number = f"+263{to_number.lstrip('0')}"

            logger.info(f"Sending SMS to {to_number}")

            # Create and send the message
            twilio_message = self.client.messages.create(
                body=message,
                from_=self.twilio_config.phone_number,
                to=to_number
            )

            logger.info(f"SMS sent successfully. SID: {twilio_message.sid}")
            return True, twilio_message.sid

        except TwilioRestException as e:
            logger.error(f"Twilio error sending SMS: {str(e)}")
            return False, None
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return False, None

    def send_found_notification(self, to_number: str, missing_person_name: str) -> bool:
        """
        Send a notification SMS when a missing person is found

        Args:
            to_number: Recipient phone number
            missing_person_name: Name of the missing person

        Returns:
            bool: True if SMS sent successfully, False otherwise
        """
        message = f"POLICE NOTIFICATION: {missing_person_name} has been located. Please contact the police department at (040) 2717860 for more information."
        success, _ = self.send_sms(to_number, message)
        return success