# ===== shared/utils/location_utils.py =====
from src.modules.records.domain.models.location import Location
from src.modules.records.domain.repositories.location_repository import LocationRepository
from src.modules.records.presentation.dtos.record_management import CreateLocationRequest, LocationResponse, \
    GetNearbyLocationsRequest, GetNearbyLocationsResponse
from src.shared.configs.exceptions.exceptions import ValidationException, NotFoundException


class LocationUtils:
    """Utility class for location management operations."""

    def __init__(self):
        self.location_repo = LocationRepository()

    def create_location(self, request: CreateLocationRequest) -> LocationResponse:
        """
        Create a new location.

        Args:
            request: CreateLocationRequest DTO

        Returns:
            LocationResponse DTO

        Raises:
            ValidationException: If location data is invalid
        """
        try:
            # Create location entity
            location = Location(
                latitude=request.latitude,
                longitude=request.longitude,
                address=request.address,
                city=request.city,
                state=request.state,
                country=request.country,
                postal_code=request.postal_code,
                description=request.description,
                created_by=request.created_by
            )

            # Save to database
            saved_location = self.location_repo.create(location)

            # Return response DTO
            return LocationResponse(
                id=saved_location.id,
                latitude=saved_location.latitude,
                longitude=saved_location.longitude,
                address=saved_location.address,
                city=saved_location.city,
                state=saved_location.state,
                country=saved_location.country,
                postal_code=saved_location.postal_code,
                description=saved_location.description,
                created_at=saved_location.created_at.isoformat(),
                updated_at=saved_location.updated_at.isoformat()
            )

        except Exception as e:
            raise ValidationException(f"Failed to create location: {str(e)}")

    def get_location_by_id(self, location_id: str) -> LocationResponse:
        """
        Get location by ID.

        Args:
            location_id: Location ID

        Returns:
            LocationResponse DTO

        Raises:
            NotFoundException: If location not found
        """
        location = self.location_repo.find_by_id(location_id)

        if not location:
            raise NotFoundException(f"Location with ID {location_id} not found")

        return LocationResponse(
            id=location.id,
            latitude=location.latitude,
            longitude=location.longitude,
            address=location.address,
            city=location.city,
            state=location.state,
            country=location.country,
            postal_code=location.postal_code,
            description=location.description,
            created_at=location.created_at.isoformat(),
            updated_at=location.updated_at.isoformat()
        )

    def get_nearby_locations(self, request: GetNearbyLocationsRequest) -> GetNearbyLocationsResponse:
        """
        Find locations near GPS coordinates.

        Args:
            request: GetNearbyLocationsRequest DTO

        Returns:
            GetNearbyLocationsResponse DTO
        """
        locations = self.location_repo.find_by_coordinates(
            latitude=request.latitude,
            longitude=request.longitude,
            radius_km=request.radius_km
        )

        location_dicts = [
            LocationResponse(
                id=loc.id,
                latitude=loc.latitude,
                longitude=loc.longitude,
                address=loc.address,
                city=loc.city,
                state=loc.state,
                country=loc.country,
                postal_code=loc.postal_code,
                description=loc.description,
                created_at=loc.created_at.isoformat(),
                updated_at=loc.updated_at.isoformat()
            ).to_dict()
            for loc in locations
        ]

        return GetNearbyLocationsResponse(
            message=f"Found {len(locations)} locations within {request.radius_km}km",
            locations=location_dicts,
            total=len(locations)
        )

    def delete_location(self, location_id: str) -> bool:
        """
        Soft delete a location.

        Args:
            location_id: Location ID

        Returns:
            True if deleted successfully

        Raises:
            NotFoundException: If location not found
        """
        location = self.location_repo.find_by_id(location_id)

        if not location:
            raise NotFoundException(f"Location with ID {location_id} not found")

        self.location_repo.delete(location)
        return True