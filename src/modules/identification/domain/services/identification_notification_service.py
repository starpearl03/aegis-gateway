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
from src.shared.configs.exceptions.exceptions import NotFoundException, ValidationException
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
            ValidationException: If person is not a missing person
        """
        # Verify search exists
        search = self.search_repo.find_by_id(request.search_id)
        if not search:
            raise NotFoundException(f"Search with ID {request.search_id} not found")

        # Verify person exists and is a missing person
        missing_person = self.missing_person_repo.find_by_id(request.person_id)
        if not missing_person:
            raise NotFoundException(f"Missing person with ID {request.person_id} not found")

        # Get reporter information
        reporter = self.reporter_repo.find_by_missing_person(request.person_id)
        if not reporter:
            raise NotFoundException(f"No reporter found for missing person {request.person_id}")

        try:
            person_name = f"{missing_person.first_name} {missing_person.last_name}"
            reporter_name = f"{reporter.first_name} {reporter.last_name}"

            # Prepare email recipient
            email_recipient = EmailRecipient(
                recipient_name=reporter_name,
                recipient_email=reporter.email if reporter.email else "",
                missing_person_name=person_name,
                missing_date=missing_person.last_seen_date.strftime("%B %d, %Y")
            )

            # Send notification via email and SMS
            notification_request = FoundNotificationRequest(
                email_recipient=email_recipient,
                mobile_number=reporter.phone_number
            )

            result = self.notification_service.send_email_sms_notification(notification_request)

            notifications_sent = 0
            if result.email_sent:
                notifications_sent += 1
            if result.sms_sent:
                notifications_sent += 1

            logger.info(
                f"Sent {notifications_sent} notification(s) for missing person {person_name} "
                f"to reporter {reporter_name}"
            )

            # Prepare reporter contact details
            reporter_contacts = [{
                'name': reporter_name,
                'email': reporter.email,
                'phone': reporter.phone_number,
                'relationship': reporter.relationship.value if reporter.relationship else None,
                'email_sent': result.email_sent,
                'sms_sent': result.sms_sent
            }]

            return SendMissingPersonNotificationResponse(
                message="Notification sent successfully" if result.success else "Failed to send notification",
                search_id=request.search_id,
                person_id=request.person_id,
                person_name=person_name,
                notifications_sent=notifications_sent,
                reporter_contacts=reporter_contacts
            )

        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}", exc_info=True)
            raise ValidationException(f"Failed to send notification: {str(e)}")
