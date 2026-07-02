import os
import logging
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape, Template
from jinja2.exceptions import TemplateNotFound

from src.shared.configs.exceptions.exceptions import InternalServerException, ServiceUnavailableException
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
        Send notifications about a found missing person via email and SMS

        Args:
            request: FoundNotificationRequest containing recipient and missing person details

        Returns:
            NotificationResult with success status and details of each notification
        """
        email_sent = False
        sms_sent = False
        error_message = None

        try:
            # Send email notification
            email_sent = self._send_email_found_notification(request.email_recipient)

            # Send SMS notification if mobile number provided
            if request.mobile_number:
                sms_message = f"{request.email_recipient.missing_person_name} reported missing has been found. Contact (040)2717860, Morris Deport, for details."
                sms_sent = self._send_sms_notification(request.mobile_number, sms_message)

            success = email_sent or sms_sent

            return NotificationResult(
                success=success,
                email_sent=email_sent,
                sms_sent=sms_sent
            )

        except Exception as e:
            logger.error(f"Error sending found notifications: {e}", exc_info=True)
            return NotificationResult(
                success=False,
                email_sent=email_sent,
                sms_sent=sms_sent,
                error_message=str(e)
            )

    def broadcast_sms(self, request: BroadcastSMSRequest) -> BroadcastResult:
        """
        Broadcast SMS message to multiple recipients (for crime alerts or missing person alerts)

        Args:
            request: BroadcastSMSRequest containing list of mobile numbers and message

        Returns:
            BroadcastResult with statistics of the broadcast operation
        """
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
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Load template
            try:
                template = self.template_env.get_template('found_notification.html')
            except TemplateNotFound:
                raise InternalServerException(
                    "Found notification template not found",
                    details=["Template file: found_notification.html is missing"]
                )

            # Render template
            html_content = template.render(
                recipient_name=email_recipient.recipient_name,
                missing_person_name=email_recipient.missing_person_name,
                missing_date=email_recipient.missing_date,
                current_year=datetime.now().strftime("%B %d, %Y")
            )

            # Send email
            success = self.mail_service.send_email(
                subject="Update on Missing Person Case",
                recipient=email_recipient.recipient_email,
                body=html_content,
                is_html=True
            )

            if success:
                logger.info(f"Found notification email sent to {email_recipient.recipient_email}")
            else:
                logger.error(f"Failed to send found notification email to {email_recipient.recipient_email}")

            return success

        except (InternalServerException, ServiceUnavailableException):
            raise
        except Exception as e:
            logger.error(f"Failed to send found notification: {e}", exc_info=True)
            return False

    def _send_sms_notification(self, mobile_number: str, user_sms: str) -> tuple[bool, Optional[str]]:
        """
        Send SMS notification with custom message

        Args:
            mobile_number: Recipient's mobile number
            user_sms: The SMS message content to send

        Returns:
            tuple: (success: bool, message_sid: Optional[str])
        """
        try:
            if not mobile_number:
                logger.info("No mobile number provided. Skipping SMS notification.")
                return False, None

            # Render SMS content from template
            template = Template(self.SMS_TEMPLATE)
            sms_content = template.render(user_sms=user_sms)

            logger.info(f"Sending SMS notification to {mobile_number}")
            success, message_sid = self.sms_service.send_sms(mobile_number, sms_content)

            if success:
                logger.info(f"SMS notification sent successfully (SID: {message_sid})")
            else:
                logger.error(f"Failed to send SMS notification to {mobile_number}")

            return success, message_sid

        except Exception as e:
            logger.error(f"Failed to send SMS notification: {e}", exc_info=True)
            return False, None