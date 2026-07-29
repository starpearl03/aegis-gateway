# ===== src/modules/identification/application/services/identification_notification_service.py =====
import logging

from src.modules.identification.domain.repositories.dentification_search_repository import \
    IdentificationSearchRepository
from src.modules.identification.domain.repositories.identification_result_repository import \
    IdentificationResultRepository
from src.modules.identification.presentation.dtos.identification_dtos import SendMissingPersonNotificationRequest, \
    SendMissingPersonNotificationResponse
from src.modules.records.domain.repositories.missing_person_repository import MissingPersonRepository
from src.modules.records.domain.repositories.reporter_repository import ReporterRepository
from src.shared.configs.exceptions.exceptions import (
    NotFoundException,
    ValidationException,
    ServiceUnavailableException,
    BadRequestException
)
from src.shared.utils.notifications.notification_service import (
    NotificationService,
    FoundNotificationRequest,
    EmailRecipient
)

logger = logging.getLogger(__name__)


class IdentificationNotificationService:
    """Service for sending notifications when missing persons are identified."""

    def __init__(self):
        self.search_repo = IdentificationSearchRepository()
        self.result_repo = IdentificationResultRepository()
        self.missing_person_repo = MissingPersonRepository()
        self.reporter_repo = ReporterRepository()
        self.notification_service = NotificationService()

    def send_missing_person_found_notification(
            self,
            request: SendMissingPersonNotificationRequest
    ) -> SendMissingPersonNotificationResponse:
        """
        Send notification to reporters when a missing person is identified.

        Args:
            request: SendMissingPersonNotificationRequest DTO

        Returns:
            SendMissingPersonNotificationResponse DTO

        Raises:
            NotFoundException: If search, person, or reporter not found
            ValidationException: If notification fails or validation errors occur
            BadRequestException: If request data is invalid
            ServiceUnavailableException: If notification service is unavailable
        """
        # Validate request
        if not request.search_id or not request.person_id:
            raise BadRequestException(
                "Invalid notification request",
                details=["Both search_id and person_id are required"]
            )

        # Verify search exists
        search = self.search_repo.find_by_id(request.search_id)
        if not search:
            raise NotFoundException(
                f"Search not found",
                details=[f"No search found with ID: {request.search_id}"]
            )

        # Verify person exists and is a missing person
        missing_person = self.missing_person_repo.find_by_id(request.person_id)
        if not missing_person:
            raise NotFoundException(
                f"Missing person not found",
                details=[f"No missing person found with ID: {request.person_id}"]
            )

        # Get reporter information
        reporter = self.reporter_repo.find_by_missing_person(request.person_id)
        if not reporter:
            raise NotFoundException(
                f"Reporter not found",
                details=[
                    f"No reporter registered for missing person with ID: {request.person_id}",
                    "A reporter must be registered before notifications can be sent"
                ]
            )

        person_name = f"{missing_person.first_name} {missing_person.last_name}"
        reporter_name = f"{reporter.first_name} {reporter.last_name}"

        # Validate we have contact information
        has_email = bool(reporter.email and reporter.email.strip())
        has_phone = bool(reporter.phone_number and reporter.phone_number.strip())

        if not has_email and not has_phone:
            raise ValidationException(
                "No contact information available",
                details=[
                    f"Reporter {reporter_name} has no contact information",
                    "Email or phone number is required to send notifications",
                    "Please update reporter contact information in the system"
                ]
            )

        # Log what we're about to attempt
        contact_methods = []
        if has_email:
            contact_methods.append(f"email: {reporter.email}")
        if has_phone:
            contact_methods.append(f"SMS: {reporter.phone_number}")

        logger.info(
            f"📤 Attempting to send notification for missing person '{person_name}' "
            f"to reporter '{reporter_name}' via {', '.join(contact_methods)}"
        )

        try:
            # Prepare email recipient
            email_recipient = EmailRecipient(
                recipient_name=reporter_name,
                recipient_email=reporter.email if has_email else "",
                missing_person_name=person_name,
                missing_date=missing_person.last_seen_date.strftime("%B %d, %Y")
            )

            # Send notification via email and SMS - will raise exception if all fail
            notification_request = FoundNotificationRequest(
                email_recipient=email_recipient,
                mobile_number=reporter.phone_number if has_phone else None
            )

            result = self.notification_service.send_email_sms_notification(notification_request)

            # Count successful notifications
            notifications_sent = sum([result.email_sent, result.sms_sent])

            # Mark notification as sent in the search record
            self.search_repo.mark_notification_sent(search)

            # Prepare success message
            sent_methods = []
            if result.email_sent:
                sent_methods.append("email")
            if result.sms_sent:
                sent_methods.append("SMS")

            success_message = (
                f"Successfully sent {notifications_sent} notification(s) "
                f"({', '.join(sent_methods)}) to {reporter_name}"
            )

            # Log partial failures if any
            if result.error_message:
                logger.warning(
                    f"⚠️ Partial notification success for {person_name}: {result.error_message}"
                )
                success_message += f". Note: {result.error_message}"

            logger.info(f"✅ {success_message}")

            # Prepare reporter contact details for response
            reporter_contacts = [{
                'name': reporter_name,
                'email': reporter.email,
                'phone': reporter.phone_number,
                'relationship': reporter.relationship.value if reporter.relationship else None,
                'email_sent': result.email_sent,
                'sms_sent': result.sms_sent
            }]

            return SendMissingPersonNotificationResponse(
                message=success_message,
                search_id=request.search_id,
                person_id=request.person_id,
                person_name=person_name,
                notifications_sent=notifications_sent,
                reporter_contacts=reporter_contacts
            )

        except BadRequestException:
            # Re-raise as-is (no contact info provided)
            raise

        except ValidationException as e:
            # Notification validation failed - enhance error message
            error_msg = f"Failed to send notification to {reporter_name}: {e.message}"
            logger.error(f"❌ {error_msg}")

            # Add helpful context to the error
            details = list(e.details) if e.details else []
            details.extend([
                f"Reporter: {reporter_name}",
                f"Missing person: {person_name}",
                f"Email available: {'Yes' if has_email else 'No'}",
                f"Phone available: {'Yes' if has_phone else 'No'}"
            ])

            raise ValidationException(error_msg, details=details)

        except ServiceUnavailableException as e:
            # Service unavailable - enhance error message
            error_msg = f"Notification service unavailable while notifying {reporter_name}"
            logger.error(f"❌ {error_msg}: {e.message}")

            details = list(e.details) if e.details else []
            details.insert(0, f"Could not send notification to {reporter_name}")

            raise ServiceUnavailableException(error_msg, details=details)

        except Exception as e:
            # Unexpected error
            error_msg = f"Unexpected error sending notification to {reporter_name}"
            logger.error(f"❌ {error_msg}: {str(e)}", exc_info=True)

            raise ValidationException(
                error_msg,
                details=[
                    str(e),
                    f"Reporter: {reporter_name}",
                    f"Missing person: {person_name}",
                    "Check application logs for full error details"
                ]
            )