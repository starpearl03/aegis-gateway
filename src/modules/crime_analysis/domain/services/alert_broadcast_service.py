# src/modules/analysis/application/services/alert_broadcast_service.py
import json
import os
import logging
from typing import List, Dict
from datetime import datetime

from src.modules.crime_analysis.domain.repositories.alert_broadcast_repository import AlertBroadcastRepository
from src.modules.crime_analysis.domain.repositories.crime_hotspot_repository import CrimeHotspotRepository
from src.modules.crime_analysis.presentation.dtos.analysis_dtos import (
    CreateAlertBroadcastRequest,
    UpdateAlertBroadcastRequest,
    AlertBroadcastResponse,
    ListAlertBroadcastsRequest,
    ListAlertBroadcastsResponse,
    DeleteResponse
)

from src.modules.crime_analysis.domain.models.alert_broadcast import AlertBroadcast
from src.modules.crime_analysis.domain.models.enums import BroadcastStatus
from src.modules.records.domain.repositories.location_repository import LocationRepository
from src.shared.configs.exceptions.exceptions import (
    NotFoundException,
    ValidationException,
    InternalServerException
)
from src.shared.utils.notifications.notification_service import NotificationService, BroadcastSMSRequest

logger = logging.getLogger(__name__)


class AlertBroadcastService:
    """Service for managing and sending alert broadcasts to all registered contacts."""

    def __init__(self):
        self.alert_repo = AlertBroadcastRepository()
        self.hotspot_repo = CrimeHotspotRepository()
        self.location_repo = LocationRepository()
        self.notification_service = NotificationService()

        # Load contact numbers
        self.contacts = self._load_contacts()

    def _load_contacts(self) -> List[str]:
        """
        Load contact numbers from JSON file.

        Returns:
            List of phone numbers
        """
        try:
            data_file = "broadcast_contacts.json"

            if not os.path.exists(data_file):
                logger.warning(f"Contacts file not found: {data_file}")
                return []

            with open(data_file, 'r') as f:
                data = json.load(f)
                contacts = data.get('contacts', [])

                if not contacts:
                    logger.warning("No contacts found in broadcast_contacts.json")
                    return []

                logger.info(f"Loaded {len(contacts)} contact numbers from broadcast_contacts.json")
                return contacts

        except Exception as e:
            logger.error(f"Error loading contacts: {e}", exc_info=True)
            return []

    # ========================================================================
    # ALERT BROADCAST MANAGEMENT
    # ========================================================================

    def create_alert_broadcast(self, request: CreateAlertBroadcastRequest) -> AlertBroadcastResponse:
        """
        Create a new alert broadcast (without sending yet).

        Args:
            request: CreateAlertBroadcastRequest DTO

        Returns:
            AlertBroadcastResponse DTO

        Raises:
            NotFoundException: If hotspot not found
            ValidationException: If validation fails
        """
        # Verify hotspot exists
        hotspot = self.hotspot_repo.find_by_id(request.hotspot_id)
        if not hotspot:
            raise NotFoundException(f"Crime hotspot with ID {request.hotspot_id} not found")

        # Get recipient count
        recipient_count = len(self.contacts)

        try:
            alert = AlertBroadcast(
                hotspot_id=request.hotspot_id,
                message=request.message,
                recipient_count=recipient_count,
                status=BroadcastStatus.PENDING
            )

            saved_alert = self.alert_repo.create(alert)
            logger.info(f"Alert broadcast created with ID {saved_alert.id} for hotspot {request.hotspot_id}")

            return self._build_alert_broadcast_response(saved_alert)

        except Exception as e:
            raise ValidationException(f"Failed to create alert broadcast: {str(e)}")

    def get_recipient_count(self, location_id: str = None) -> int:
        """
        Get the number of recipients (location_id not used, kept for compatibility).

        Args:
            location_id: Not used, kept for backward compatibility

        Returns:
            Number of recipients
        """
        return len(self.contacts)

    def send_alert_broadcast(self, alert_id: str, is_resend: bool = False) -> AlertBroadcastResponse:
        """
        Send an alert broadcast to all contacts.

        Args:
            alert_id: Alert broadcast ID
            is_resend: Whether this is a resend operation (allows sending already-sent alerts)

        Returns:
            Updated AlertBroadcastResponse DTO

        Raises:
            NotFoundException: If alert not found
            ValidationException: If alert already sent (unless is_resend=True) or has no recipients
        """
        # Get alert
        alert = self.alert_repo.find_by_id(alert_id)
        if not alert:
            raise NotFoundException(f"Alert broadcast with ID {alert_id} not found")

        # Check if already sent (only block if not a resend)
        if not is_resend and alert.status == BroadcastStatus.SENT:
            raise ValidationException("Alert broadcast has already been sent. Use resend if you want to send it again.")

        # Get hotspot (for logging purposes)
        hotspot = self.hotspot_repo.find_by_id(alert.hotspot_id)
        if not hotspot:
            raise NotFoundException(f"Crime hotspot with ID {alert.hotspot_id} not found")

        # Check if we have contacts
        if not self.contacts:
            logger.warning("No contacts available for broadcast")
            alert.status = BroadcastStatus.FAILED
            alert.recipient_count = 0
            self.alert_repo.update(alert)
            raise ValidationException("No contact numbers available for broadcast")

        try:
            action = "Resending" if is_resend else "Sending"
            logger.info(f"{action} alert broadcast to {len(self.contacts)} recipients")

            # Send SMS broadcast
            broadcast_request = BroadcastSMSRequest(
                mobile_numbers=self.contacts,
                message=alert.message
            )

            result = self.notification_service.broadcast_sms(broadcast_request)

            # Update alert based on result
            alert.sent_at = datetime.now()
            alert.recipient_count = result.successful_sends

            if result.success and result.successful_sends > 0:
                alert.status = BroadcastStatus.SENT
                logger.info(
                    f"Alert broadcast {alert_id} {'resent' if is_resend else 'sent'} successfully to "
                    f"{result.successful_sends}/{result.total_recipients} recipients"
                )
            else:
                alert.status = BroadcastStatus.FAILED
                logger.error(f"Alert broadcast {alert_id} failed to send to all recipients")

            updated_alert = self.alert_repo.update(alert)

            return self._build_alert_broadcast_response(updated_alert)

        except Exception as e:
            # Update alert as failed
            alert.status = BroadcastStatus.FAILED
            self.alert_repo.update(alert)
            logger.error(f"Error sending alert broadcast {alert_id}: {e}", exc_info=True)
            raise InternalServerException(f"Failed to send alert broadcast: {str(e)}")

    def resend_alert_broadcast(self, alert_id: str) -> AlertBroadcastResponse:
        """
        Resend an already-sent alert broadcast.
        This is a convenience wrapper around send_alert_broadcast with is_resend=True.

        Args:
            alert_id: Alert broadcast ID

        Returns:
            Updated AlertBroadcastResponse DTO
        """
        return self.send_alert_broadcast(alert_id, is_resend=True)

    def update_alert_broadcast(self, request: UpdateAlertBroadcastRequest) -> AlertBroadcastResponse:
        """
        Update alert broadcast details.

        Args:
            request: UpdateAlertBroadcastRequest DTO

        Returns:
            AlertBroadcastResponse DTO

        Raises:
            NotFoundException: If alert not found
            ValidationException: If update data is invalid
        """
        alert = self.alert_repo.find_by_id(request.alert_id)
        if not alert:
            raise NotFoundException(f"Alert broadcast with ID {request.alert_id} not found")

        try:
            if request.status is not None:
                alert.status = self._get_enum_by_value(BroadcastStatus, request.status)
            if request.sent_at is not None:
                alert.sent_at = datetime.fromisoformat(request.sent_at)
            if request.recipient_count is not None:
                alert.recipient_count = request.recipient_count

            updated_alert = self.alert_repo.update(alert)
            return self._build_alert_broadcast_response(updated_alert)

        except Exception as e:
            raise ValidationException(f"Failed to update alert broadcast: {str(e)}")

    def get_alert_broadcast_by_id(self, alert_id: str) -> AlertBroadcastResponse:
        """
        Get alert broadcast by ID.

        Args:
            alert_id: Alert broadcast ID

        Returns:
            AlertBroadcastResponse DTO

        Raises:
            NotFoundException: If alert not found
        """
        alert = self.alert_repo.find_by_id(alert_id)
        if not alert:
            raise NotFoundException(f"Alert broadcast with ID {alert_id} not found")

        return self._build_alert_broadcast_response(alert)

    def list_alert_broadcasts(self, request: ListAlertBroadcastsRequest) -> ListAlertBroadcastsResponse:
        """
        List alert broadcasts with filters and pagination.

        Args:
            request: ListAlertBroadcastsRequest DTO

        Returns:
            ListAlertBroadcastsResponse DTO
        """
        # Build query based on filters
        if request.hotspot_id:
            alerts = self.alert_repo.find_by_hotspot(request.hotspot_id)
        elif request.status:
            status = self._get_enum_by_value(BroadcastStatus, request.status)
            alerts = self.alert_repo.find_by_status(status)
        else:
            alerts = self.alert_repo.find_all(include_deleted=request.include_deleted)

        # Pagination
        total = len(alerts)
        start = (request.page - 1) * request.per_page
        end = start + request.per_page
        paginated_alerts = alerts[start:end]

        alert_dicts = [
            self._build_alert_broadcast_response(alert).to_dict()
            for alert in paginated_alerts
        ]

        return ListAlertBroadcastsResponse(
            message=f"Found {total} alert broadcast(s)",
            alerts=alert_dicts,
            total=total,
            page=request.page,
            per_page=request.per_page,
            total_pages=(total + request.per_page - 1) // request.per_page
        )

    def get_pending_alerts(self) -> List[AlertBroadcastResponse]:
        """Get all pending alert broadcasts."""
        alerts = self.alert_repo.find_pending_alerts()
        return [self._build_alert_broadcast_response(alert) for alert in alerts]

    def get_recent_alerts(self, limit: int = 10) -> List[AlertBroadcastResponse]:
        """Get recently sent alert broadcasts."""
        alerts = self.alert_repo.find_recent_alerts(limit)
        return [self._build_alert_broadcast_response(alert) for alert in alerts]

    def delete_alert_broadcast(self, alert_id: str) -> DeleteResponse:
        """
        Soft delete an alert broadcast.

        Args:
            alert_id: Alert broadcast ID

        Returns:
            DeleteResponse DTO

        Raises:
            NotFoundException: If alert not found
        """
        alert = self.alert_repo.find_by_id(alert_id)
        if not alert:
            raise NotFoundException(f"Alert broadcast with ID {alert_id} not found")

        self.alert_repo.delete(alert)
        return DeleteResponse(
            message="Alert broadcast deleted successfully",
            id=alert_id
        )

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _build_alert_broadcast_response(self, alert: AlertBroadcast) -> AlertBroadcastResponse:
        """Build AlertBroadcastResponse DTO from entity."""
        return AlertBroadcastResponse(
            id=alert.id,
            hotspot_id=alert.hotspot_id,
            message=alert.message,
            sent_at=alert.sent_at.isoformat() if alert.sent_at else None,
            recipient_count=alert.recipient_count,
            status=alert.status.value,
            created_at=alert.created_at.isoformat(),
            updated_at=alert.updated_at.isoformat()
        )

    @staticmethod
    def _get_enum_by_value(enum_class, value: str):
        """Get enum member by its value (case-insensitive)."""
        if not value:
            raise ValidationException(f"Value cannot be empty for {enum_class.__name__}")

        value_lower = value.lower().strip()
        for member in enum_class:
            if member.value.lower() == value_lower:
                return member

        valid_values = [member.value for member in enum_class]
        raise ValidationException(
            f"Invalid {enum_class.__name__} value: '{value}'. "
            f"Valid options are: {', '.join(valid_values)}"
        )