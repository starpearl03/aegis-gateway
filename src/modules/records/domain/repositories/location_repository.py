# ===== shared/repositories/location_repository.py =====
from typing import List, Optional

from src.modules.records.domain.models.location import Location
from src.shared.data.base.repository import BaseRepository


class LocationRepository(BaseRepository[Location]):
    """Repository for Location model"""

    def __init__(self):
        super().__init__(Location)

    def find_by_coordinates(self, latitude: float, longitude: float,
                            radius_km: float = 1.0) -> List[Location]:
        """
        Find locations within a certain radius of given coordinates.

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            radius_km: Search radius in kilometers (default: 1.0)

        Returns:
            List of locations within the radius
        """
        # Using Haversine formula for distance calculation
        # 111.32 km per degree of latitude (approximate)
        lat_range = radius_km / 111.32
        lon_range = radius_km / (111.32 * abs(float(latitude)))

        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.latitude.between(latitude - lat_range, latitude + lat_range),
            self.model.longitude.between(longitude - lon_range, longitude + lon_range)
        ).all()

    def find_by_city(self, city: str) -> List[Location]:
        """Find all locations in a specific city"""
        return self.find_many_by({"city": city})

    def find_by_postal_code(self, postal_code: str) -> List[Location]:
        """Find all locations with a specific postal code"""
        return self.find_many_by({"postal_code": postal_code})