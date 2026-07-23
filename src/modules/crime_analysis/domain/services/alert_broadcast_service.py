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
    """Service for managing and sending alert broadcasts to locals in specific areas."""

    def __init__(self):
        self.alert_repo = AlertBroadcastRepository()
        self.hotspot_repo = CrimeHotspotRepository()
        self.location_repo = LocationRepository()
        self.notification_service = NotificationService()

        # Load location contact data
        self.location_contacts = self._load_location_contacts()

    def _load_location_contacts(self) -> Dict[str, List[str]]:
        """
        Load location-based contact numbers from JSON file.

        Returns:
            Dictionary mapping location IDs to lists of phone numbers
        """
        try:
            data_file = "broadcast_contacts.json"

            if not os.path.exists(data_file):
                logger.warning(f"Location contacts file not found: {data_file}")
                return {}

            with open(data_file, 'r') as f:
                data = json.load(f)
                logger.info(f"Loaded contact data for {len(data.get('locations', []))} locations")

                # Convert to dictionary for easy lookup
                contacts_map = {}
                for location in data.get('locations', []):
                    location_id = location.get('location_id')
                    contacts = location.get('contacts', [])
                    if location_id and contacts:
                        contacts_map[location_id] = contacts

                return contacts_map

        except Exception as e:
            logger.error(f"Error loading location contacts: {e}", exc_info=True)
            return {}

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

        # Get recipient count from location contacts
        recipient_count = self._get_recipient_count(hotspot.location_id)

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

    def get_recipient_count(self, location_id: str) -> int:
        """Get the number of recipients for a location (public method)."""
        return self._get_recipient_count(location_id)

    def send_alert_broadcast(self, alert_id: str) -> AlertBroadcastResponse:
        """
        Send an alert broadcast to all contacts in the hotspot's location.

        Args:
            alert_id: Alert broadcast ID

        Returns:
            Updated AlertBroadcastResponse DTO

        Raises:
            NotFoundException: If alert or location not found
            ValidationException: If alert already sent or has no recipients
        """
        # Get alert
        alert = self.alert_repo.find_by_id(alert_id)
        if not alert:
            raise NotFoundException(f"Alert broadcast with ID {alert_id} not found")

        # Check if already sent
        if alert.status == BroadcastStatus.SENT:
            raise ValidationException("Alert broadcast has already been sent")

        # Get hotspot and location
        hotspot = self.hotspot_repo.find_by_id(alert.hotspot_id)
        if not hotspot:
            raise NotFoundException(f"Crime hotspot with ID {alert.hotspot_id} not found")

        location = self.location_repo.find_by_id(hotspot.location_id)
        if not location:
            raise NotFoundException(f"Location with ID {hotspot.location_id} not found")

        # Get contact numbers for this location
        contact_numbers = self._get_location_contacts(hotspot.location_id)

        if not contact_numbers:
            logger.warning(f"No contacts found for location {hotspot.location_id}")
            alert.status = BroadcastStatus.FAILED
            alert.recipient_count = 0
            self.alert_repo.update(alert)
            raise ValidationException(
                f"No contact numbers available for location: {location.city or location.address}"
            )

        try:
            logger.info(f"Sending alert broadcast to {len(contact_numbers)} recipients in {location.city}")

            # Send SMS broadcast
            broadcast_request = BroadcastSMSRequest(
                mobile_numbers=contact_numbers,
                message=alert.message
            )

            result = self.notification_service.broadcast_sms(broadcast_request)

            # Update alert based on result
            alert.sent_at = datetime.now()
            alert.recipient_count = result.successful_sends

            if result.success and result.successful_sends > 0:
                alert.status = BroadcastStatus.SENT
                logger.info(
                    f"Alert broadcast {alert_id} sent successfully to "
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

    def _get_location_contacts(self, location_id: str) -> List[str]:
        """
        Get contact numbers for a specific location.

        Args:
            location_id: Location ID

        Returns:
            List of phone numbers
        """
        return self.location_contacts.get(location_id, [])

    def _get_recipient_count(self, location_id: str) -> int:
        """
        Get the number of recipients for a location.

        Args:
            location_id: Location ID

        Returns:
            Number of recipients
        """
        contacts = self._get_location_contacts(location_id)
        return len(contacts)

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