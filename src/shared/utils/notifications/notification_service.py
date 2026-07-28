import os
import logging
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
from jinja2.exceptions import TemplateNotFound

from src.shared.configs.exceptions.exceptions import (
    InternalServerException,
    ServiceUnavailableException,
    ValidationException,
    BadRequestException
)
from src.shared.utils.notifications.internal.mail_client import MailClient
from src.shared.utils.notifications.internal.sms_client import SMSClient

logger = logging.getLogger(__name__)


# ============================================
# DTOs
# ============================================

@dataclass
class EmailRecipient:
    """DTO for email recipient details"""
    recipient_name: str
    recipient_email: str
    missing_person_name: str
    missing_date: str


@dataclass
class FoundNotificationRequest:
    """Request DTO for sending found person notifications"""
    email_recipient: EmailRecipient
    mobile_number: Optional[str] = None


@dataclass
class BroadcastSMSRequest:
    """Request DTO for broadcasting SMS to multiple recipients"""
    mobile_numbers: List[str]
    message: str


@dataclass
class NotificationResult:
    """Result DTO for notification operations"""
    success: bool
    email_sent: bool = False
    sms_sent: bool = False
    error_message: Optional[str] = None


@dataclass
class BroadcastResult:
    """Result DTO for broadcast operations"""
    total_recipients: int
    successful_sends: int
    failed_sends: int
    failed_numbers: List[str]
    success: bool


# ============================================
# Service
# ============================================

class NotificationService:
    """Service for sending email and SMS notifications"""

    SMS_TEMPLATE = "POLICE ALERT: {{user_sms}} -Forensic Dept"

    def __init__(self):
        """Initialize notification service with mail and SMS clients"""
        self.mail_service = MailClient()
        self.sms_service = SMSClient()

        # Setup Jinja2 environment for template loading
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(current_dir, "internal", "templates")

        # Validate template directory exists
        if not os.path.exists(template_dir):
            raise InternalServerException(
                f"Email template directory not found: {template_dir}",
                details=["Please ensure internal/templates directory exists"]
            )

        self.template_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )

    def send_email_sms_notification(self, request: FoundNotificationRequest) -> NotificationResult:
        """
        Send notifications about a found missing person via email and SMS.
        Raises exceptions if notifications fail.

        Args:
            request: FoundNotificationRequest containing recipient and missing person details

        Returns:
            NotificationResult with success status and details of each notification

        Raises:
            ValidationException: If contact information is invalid or notifications fail
            BadRequestException: If no contact information is provided
            ServiceUnavailableException: If notification service is unavailable
        """
        email_sent = False
        sms_sent = False
        email_error = None
        sms_error = None

        # Validate that we have at least one contact method
        has_email = bool(request.email_recipient.recipient_email and
                         request.email_recipient.recipient_email.strip())
        has_mobile = bool(request.mobile_number and request.mobile_number.strip())

        if not has_email and not has_mobile:
            raise BadRequestException(
                "No contact information provided",
                details=["At least one contact method (email or mobile number) is required"]
            )

        # Track which notifications we attempted and their results
        attempted_methods = []
        failed_methods = []

        # Try to send email notification
        if has_email:
            attempted_methods.append(f"email to {request.email_recipient.recipient_email}")
            try:
                email_sent = self._send_email_found_notification(request.email_recipient)
                logger.info(f"✅ Email notification sent to {request.email_recipient.recipient_email}")
            except (InternalServerException, ServiceUnavailableException, ValidationException) as e:
                # These are already formatted exceptions from the email method
                email_error = f"{e.message}: {', '.join(e.details) if e.details else ''}"
                failed_methods.append(f"Email to {request.email_recipient.recipient_email}: {email_error}")
                logger.error(f"❌ Email notification failed: {email_error}")
            except Exception as e:
                email_error = str(e)
                failed_methods.append(f"Email to {request.email_recipient.recipient_email}: {email_error}")
                logger.error(f"❌ Email notification failed: {e}", exc_info=True)

        # Try to send SMS notification if mobile number provided
        if has_mobile:
            attempted_methods.append(f"SMS to {request.mobile_number}")
            try:
                sms_message = (
                    f"{request.email_recipient.missing_person_name} reported missing has been found. "
                    f"Contact (040)2717860, Morris Deport, for details."
                )
                sms_sent, message_sid = self._send_sms_notification(
                    request.mobile_number,
                    sms_message
                )
                logger.info(f"✅ SMS notification sent to {request.mobile_number} (SID: {message_sid})")
            except (ServiceUnavailableException, ValidationException) as e:
                # These are already formatted exceptions from the SMS method
                sms_error = f"{e.message}: {', '.join(e.details) if e.details else ''}"
                failed_methods.append(f"SMS to {request.mobile_number}: {sms_error}")
                logger.error(f"❌ SMS notification failed: {sms_error}")
            except Exception as e:
                sms_error = str(e)
                failed_methods.append(f"SMS to {request.mobile_number}: {sms_error}")
                logger.error(f"❌ SMS notification failed: {e}", exc_info=True)

        # Determine overall success
        at_least_one_succeeded = email_sent or sms_sent
        all_failed = not at_least_one_succeeded

        # If all notifications failed, raise exception with details
        if all_failed:
            error_details = [
                                f"Attempted {len(attempted_methods)} notification(s), all failed:"
                            ] + failed_methods

            logger.error(f"❌ All notifications failed. Attempted: {', '.join(attempted_methods)}")

            raise ValidationException(
                "Failed to send any notifications",
                details=error_details
            )

        # If some failed but at least one succeeded, log warning but return success
        if failed_methods:
            logger.warning(
                f"⚠️ Partial notification success: "
                f"{sum([email_sent, sms_sent])}/{len(attempted_methods)} succeeded. "
                f"Failed: {', '.join(failed_methods)}"
            )

        # Return result
        return NotificationResult(
            success=True,
            email_sent=email_sent,
            sms_sent=sms_sent,
            error_message="; ".join(failed_methods) if failed_methods else None
        )

    def broadcast_sms(self, request: BroadcastSMSRequest) -> BroadcastResult:
        """
        Broadcast SMS message to multiple recipients (for crime alerts or missing person alerts)

        Args:
            request: BroadcastSMSRequest containing list of mobile numbers and message

        Returns:
            BroadcastResult with statistics of the broadcast operation
        """
        if not request.mobile_numbers:
            raise BadRequestException(
                "No mobile numbers provided for broadcast",
                details=["At least one mobile number is required"]
            )

        total_recipients = len(request.mobile_numbers)
        successful_sends = 0
        failed_numbers = []

        logger.info(f"Broadcasting SMS to {total_recipients} recipients")

        for mobile_number in request.mobile_numbers:
            try:
                success, message_sid = self._send_sms_notification(mobile_number, request.message)

                if success:
                    successful_sends += 1
                    logger.info(f"SMS sent successfully to {mobile_number} (SID: {message_sid})")
                else:
                    failed_numbers.append(mobile_number)
                    logger.warning(f"Failed to send SMS to {mobile_number}")

            except Exception as e:
                failed_numbers.append(mobile_number)
                logger.error(f"Error sending SMS to {mobile_number}: {e}")

        failed_sends = len(failed_numbers)
        success = successful_sends > 0

        logger.info(
            f"Broadcast completed: {successful_sends}/{total_recipients} successful, "
            f"{failed_sends} failed"
        )

        return BroadcastResult(
            total_recipients=total_recipients,
            successful_sends=successful_sends,
            failed_sends=failed_sends,
            failed_numbers=failed_numbers,
            success=success
        )

    def _send_email_found_notification(self, email_recipient: EmailRecipient) -> bool:
        """
        Send email notification when a missing person is found

        Args:
            email_recipient: EmailRecipient DTO containing recipient and missing person details

        Returns:
            bool: True if email sent successfully

        Raises:
            InternalServerException: If template not found or rendering fails
            ServiceUnavailableException: If email service is unavailable (captures actual SMTP error)
            ValidationException: If email address is invalid
        """
        # Validate email recipient
        if not email_recipient.recipient_email or not email_recipient.recipient_email.strip():
            raise ValidationException(
                "Invalid email recipient",
                details=["Email address is required and cannot be empty"]
            )

        try:
            # Load template
            try:
                template = self.template_env.get_template('found_notification.html')
            except TemplateNotFound:
                raise InternalServerException(
                    "Found notification template not found",
                    details=["Template file: found_notification.html is missing from internal/templates/"]
                )

            # Render template
            try:
                html_content = template.render(
                    recipient_name=email_recipient.recipient_name,
                    missing_person_name=email_recipient.missing_person_name,
                    missing_date=email_recipient.missing_date,
                    current_year=datetime.now().strftime("%B %d, %Y")
                )
            except Exception as e:
                raise InternalServerException(
                    "Failed to render email template",
                    details=[f"Template rendering error: {str(e)}"]
                )

            # Send email - this is where we capture the ACTUAL error from mail_client
            try:
                success = self.mail_service.send_email(
                    subject="Update on Missing Person Case",
                    recipient=email_recipient.recipient_email,
                    body=html_content,
                    is_html=True
                )

                if not success:
                    # Mail service returned False - it should have logged the actual error
                    # Check the logs from mail_client for the real reason
                    raise ServiceUnavailableException(
                        "Email service failed to send message",
                        details=[
                            f"Failed to send email to {email_recipient.recipient_email}",
                            "Check application logs for SMTP connection errors"
                        ]
                    )

                logger.info(f"Found notification email sent to {email_recipient.recipient_email}")
                return True

            except Exception as e:
                # This catches actual SMTP errors from mail_client
                error_message = str(e)
                logger.error(f"SMTP Error: {error_message}", exc_info=True)

                raise ServiceUnavailableException(
                    "Email service error",
                    details=[
                        f"SMTP Error: {error_message}",
                        f"Recipient: {email_recipient.recipient_email}"
                    ]
                )

        except (InternalServerException, ServiceUnavailableException, ValidationException):
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}", exc_info=True)
            raise ServiceUnavailableException(
                "Unexpected email error",
                details=[f"Error: {str(e)}"]
            )

    def _send_sms_notification(self, mobile_number: str, user_sms: str) -> tuple[bool, Optional[str]]:
        """
        Send SMS notification with custom message

        Args:
            mobile_number: Recipient's mobile number
            user_sms: The SMS message content to send

        Returns:
            tuple: (success: bool, message_sid: Optional[str])

        Raises:
            ValidationException: If mobile number is invalid
            ServiceUnavailableException: If SMS service fails (captures actual Twilio error)
        """
        # Validate mobile number
        if not mobile_number or not mobile_number.strip():
            raise ValidationException(
                "Invalid mobile number",
                details=["Mobile number is required and cannot be empty"]
            )

        try:
            # Render SMS content from template
            template = Template(self.SMS_TEMPLATE)
            sms_content = template.render(user_sms=user_sms)

            logger.info(f"Attempting to send SMS to {mobile_number}")

            # This is where we capture the ACTUAL error from sms_client
            try:
                success, message_sid = self.sms_service.send_sms(mobile_number, sms_content)

                if not success:
                    # SMS service returned False - it should have logged the actual Twilio error
                    # Check the logs from sms_client for the real reason
                    raise ServiceUnavailableException(
                        "SMS service failed to send message",
                        details=[
                            f"Failed to send SMS to {mobile_number}",
                            "Check application logs for Twilio error details",
                            "Common causes: invalid number format, unverified number (trial account), invalid credentials"
                        ]
                    )

                logger.info(f"SMS sent successfully (SID: {message_sid})")
                return success, message_sid

            except Exception as e:
                # This catches actual Twilio errors from sms_client
                error_message = str(e)
                logger.error(f"Twilio Error: {error_message}", exc_info=True)

                raise ServiceUnavailableException(
                    "SMS service error",
                    details=[
                        f"Twilio Error: {error_message}",
                        f"Recipient: {mobile_number}"
                    ]
                )

        except (ValidationException, ServiceUnavailableException):
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending SMS: {e}", exc_info=True)
            raise ServiceUnavailableException(
                "Unexpected SMS error",
                details=[f"Error: {str(e)}"]
            )