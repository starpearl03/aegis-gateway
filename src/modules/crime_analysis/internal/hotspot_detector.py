# src/modules/analysis/internal/hotspot_detector.py
import logging
from typing import List, Dict, Any
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from sklearn.cluster import DBSCAN
from geopy.distance import great_circle

from src.modules.records.domain.models.crime import Crime
from src.modules.records.domain.models.missing_person import MissingPerson

logger = logging.getLogger(__name__)


@dataclass
class HotspotData:
    """Data structure for a detected hotspot"""
    location_id: str
    latitude: float
    longitude: float
    incident_count: int
    crime_type: str | None
    is_missing_person_hotspot: bool
    risk_level: str
    cluster_id: int
    incidents: List[Dict[str, Any]]  # Store incident details for analysis


class HotspotDetector:
    """
    Detects crime hotspots using DBSCAN clustering algorithm.
    Groups crimes and missing persons within a specified radius.
    Now clusters by crime type separately to avoid losing information.
    """

    def __init__(self, radius_km: float = 2.0, min_incidents: int = 3):
        """
        Initialize hotspot detector.

        Args:
            radius_km: Maximum distance (in km) for incidents to be in same cluster
            min_incidents: Minimum incidents required to form a hotspot cluster
        """
        self.radius_km = radius_km
        self.min_incidents = min_incidents
        self.earth_radius_km = 6371.0  # Earth's radius in kilometers

    def detect_hotspots(
            self,
            crimes: List[Crime],
            missing_persons: List[MissingPerson]
    ) -> List[HotspotData]:
        """
        Detect hotspots from crimes and missing persons using DBSCAN clustering.
        Now clusters each crime type separately to preserve all information.

        Args:
            crimes: List of Crime entities
            missing_persons: List of MissingPerson entities

        Returns:
            List of HotspotData objects representing detected hotspots
        """
        logger.info(f"Starting hotspot detection with radius={self.radius_km}km, "
                    f"min_incidents={self.min_incidents}")
        logger.info(f"Input: {len(crimes)} crimes, {len(missing_persons)} missing persons")

        all_hotspots = []

        # ✅ Process missing persons as a separate group
        if missing_persons:
            missing_locations = self._extract_missing_person_locations(missing_persons)
            if missing_locations:
                logger.info(f"Clustering {len(missing_locations)} missing person locations")
                missing_hotspots = self._cluster_and_build_hotspots(
                    missing_locations,
                    crime_type='missing_person',
                    is_missing_person=True
                )
                all_hotspots.extend(missing_hotspots)
                logger.info(f"Created {len(missing_hotspots)} missing person hotspots")

        # ✅ Group crimes by crime_type
        crime_locations = self._extract_crime_locations(crimes)
        if crime_locations:
            crimes_by_type = defaultdict(list)
            for location in crime_locations:
                crime_type = location['crime_type'] or 'unknown'
                crimes_by_type[crime_type].append(location)

            # ✅ Cluster each crime type separately
            for crime_type, locations in crimes_by_type.items():
                logger.info(f"Clustering {len(locations)} {crime_type} locations")
                crime_hotspots = self._cluster_and_build_hotspots(
                    locations,
                    crime_type=crime_type,
                    is_missing_person=False
                )
                all_hotspots.extend(crime_hotspots)
                logger.info(f"Created {len(crime_hotspots)} {crime_type} hotspots")

        # Sort all hotspots by incident count (descending)
        all_hotspots.sort(key=lambda h: h.incident_count, reverse=True)

        logger.info(f"Detected {len(all_hotspots)} total hotspots across all crime types")
        return all_hotspots

    def _cluster_and_build_hotspots(
            self,
            locations: List[Dict[str, Any]],
            crime_type: str,
            is_missing_person: bool
    ) -> List[HotspotData]:
        """
        Cluster a specific group of locations and build hotspots.

        Args:
            locations: List of location dictionaries (all same crime type)
            crime_type: The crime type for these locations
            is_missing_person: Whether these are missing person incidents

        Returns:
            List of HotspotData objects for this crime type
        """
        if len(locations) < self.min_incidents:
            logger.debug(f"Skipping {crime_type}: only {len(locations)} incidents "
                         f"(minimum required: {self.min_incidents})")
            return []

        # Perform clustering
        cluster_labels = self._cluster_locations(locations)

        # Build hotspots from clusters
        hotspots = self._build_hotspots(cluster_labels, locations, crime_type, is_missing_person)

        return hotspots

    def _extract_crime_locations(self, crimes: List[Crime]) -> List[Dict[str, Any]]:
        """Extract location data from crimes."""
        locations = []

        for crime in crimes:
            if crime.location and crime.location.latitude and crime.location.longitude:
                locations.append({
                    'type': 'crime',
                    'location_id': crime.location.id,
                    'latitude': float(crime.location.latitude),
                    'longitude': float(crime.location.longitude),
                    'crime_type': crime.crime_type,
                    'date': crime.date_committed,
                    'incident_id': crime.id,
                    'location': crime.location
                })

        logger.debug(f"Extracted {len(locations)} crime locations")
        return locations

    def _extract_missing_person_locations(
            self,
            missing_persons: List[MissingPerson]
    ) -> List[Dict[str, Any]]:
        """Extract location data from missing persons."""
        locations = []

        for mp in missing_persons:
            if mp.last_seen_location and mp.last_seen_location.latitude and mp.last_seen_location.longitude:
                locations.append({
                    'type': 'missing_person',
                    'location_id': mp.last_seen_location.id,
                    'latitude': float(mp.last_seen_location.latitude),
                    'longitude': float(mp.last_seen_location.longitude),
                    'crime_type': None,
                    'date': mp.last_seen_date,
                    'incident_id': mp.id,
                    'location': mp.last_seen_location
                })

        logger.debug(f"Extracted {len(locations)} missing person locations")
        return locations

    def _cluster_locations(self, locations: List[Dict[str, Any]]) -> np.ndarray:
        """
        Cluster locations using DBSCAN algorithm.

        Args:
            locations: List of location dictionaries

        Returns:
            Array of cluster labels (-1 for noise/outliers)
        """
        # Extract coordinates
        coordinates = np.array([[loc['latitude'], loc['longitude']] for loc in locations])

        # Convert radius from km to radians for DBSCAN
        # DBSCAN expects epsilon in radians when using haversine metric
        epsilon_radians = self.radius_km / self.earth_radius_km

        # Perform DBSCAN clustering
        # metric='haversine' uses great circle distance
        # Coordinates must be in radians for haversine
        coordinates_radians = np.radians(coordinates)

        dbscan = DBSCAN(
            eps=epsilon_radians,
            min_samples=self.min_incidents,
            metric='haversine'
        )

        cluster_labels = dbscan.fit_predict(coordinates_radians)

        # Log clustering results
        unique_clusters = set(cluster_labels)
        num_clusters = len(unique_clusters - {-1})  # Exclude noise (-1)
        num_noise = list(cluster_labels).count(-1)

        logger.debug(f"Clustering complete: {num_clusters} clusters, {num_noise} noise points")

        return cluster_labels

    def _build_hotspots(
            self,
            cluster_labels: np.ndarray,
            locations: List[Dict[str, Any]],
            crime_type: str,
            is_missing_person: bool
    ) -> List[HotspotData]:
        """
        Build hotspot data structures from clusters.

        Args:
            cluster_labels: Array of cluster labels from DBSCAN
            locations: List of location dictionaries (all same crime type)
            crime_type: The crime type for these hotspots
            is_missing_person: Whether these are missing person hotspots

        Returns:
            List of HotspotData objects
        """
        # Group locations by cluster
        clusters = defaultdict(list)
        for idx, label in enumerate(cluster_labels):
            if label != -1:  # Skip noise points
                clusters[label].append(locations[idx])

        hotspots = []

        for cluster_id, cluster_locations in clusters.items():
            hotspot = self._create_hotspot_from_cluster(
                cluster_id,
                cluster_locations,
                crime_type,
                is_missing_person
            )
            hotspots.append(hotspot)

        # Sort hotspots by incident count (descending)
        hotspots.sort(key=lambda h: h.incident_count, reverse=True)

        return hotspots

    def _create_hotspot_from_cluster(
            self,
            cluster_id: int,
            cluster_locations: List[Dict[str, Any]],
            crime_type: str,
            is_missing_person: bool
    ) -> HotspotData:
        """
        Create a HotspotData object from a cluster of locations.

        Args:
            cluster_id: Cluster identifier
            cluster_locations: List of locations in this cluster (all same crime type)
            crime_type: The crime type for this hotspot
            is_missing_person: Whether this is a missing person hotspot

        Returns:
            HotspotData object
        """
        # Calculate centroid (average lat/lng) and convert to native float
        avg_lat = float(np.mean([loc['latitude'] for loc in cluster_locations]))
        avg_lng = float(np.mean([loc['longitude'] for loc in cluster_locations]))

        # Find the most representative location_id (closest to centroid)
        location_id = self._get_representative_location_id(cluster_locations, avg_lat, avg_lng)

        # Incident count
        incident_count = len(cluster_locations)

        # Calculate risk level based on incident count
        risk_level = self._calculate_risk_level(incident_count, is_missing_person)

        # Set crime_type (None for missing persons)
        hotspot_crime_type = None if is_missing_person else crime_type

        return HotspotData(
            location_id=location_id,
            latitude=avg_lat,
            longitude=avg_lng,
            incident_count=incident_count,
            crime_type=hotspot_crime_type,
            is_missing_person_hotspot=is_missing_person,
            risk_level=risk_level,
            cluster_id=cluster_id,
            incidents=cluster_locations
        )

    def _get_representative_location_id(
            self,
            cluster_locations: List[Dict[str, Any]],
            centroid_lat: float,
            centroid_lng: float
    ) -> str:
        """
        Get the most representative location_id for the cluster.
        Uses the location closest to the centroid.

        Args:
            cluster_locations: List of locations in cluster
            centroid_lat: Cluster centroid latitude
            centroid_lng: Cluster centroid longitude

        Returns:
            Location ID string
        """
        min_distance = float('inf')
        representative_id = cluster_locations[0]['location_id']

        for loc in cluster_locations:
            distance = great_circle(
                (centroid_lat, centroid_lng),
                (loc['latitude'], loc['longitude'])
            ).kilometers

            if distance < min_distance:
                min_distance = distance
                representative_id = loc['location_id']

        return representative_id

    def _calculate_risk_level(self, incident_count: int, is_missing_person: bool) -> str:
        """
        Calculate risk level based on incident count.

        Args:
            incident_count: Number of incidents in hotspot
            is_missing_person: Whether this is a missing person hotspot

        Returns:
            Risk level string: 'low', 'medium', 'high', or 'critical'
        """
        # Adjust thresholds for missing persons (typically fewer incidents)
        if is_missing_person:
            if incident_count >= 10:
                return 'critical'
            elif incident_count >= 7:
                return 'high'
            elif incident_count >= 5:
                return 'medium'
            else:
                return 'low'
        else:
            # Crime hotspots
            if incident_count >= 15:
                return 'critical'
            elif incident_count >= 10:
                return 'high'
            elif incident_count >= 5:
                return 'medium'
            else:
                return 'low'

    def get_cluster_statistics(self, hotspots: List[HotspotData]) -> Dict[str, Any]:
        """
        Get statistics about detected hotspots.

        Args:
            hotspots: List of detected hotspots

        Returns:
            Dictionary with statistics
        """
        if not hotspots:
            return {
                'total_hotspots': 0,
                'total_incidents': 0,
                'by_risk_level': {},
                'by_type': {},
                'by_crime_type': {}
            }

        total_incidents = sum(h.incident_count for h in hotspots)

        risk_level_counts = defaultdict(int)
        type_counts = defaultdict(int)
        crime_type_counts = defaultdict(int)

        for hotspot in hotspots:
            risk_level_counts[hotspot.risk_level] += 1

            if hotspot.is_missing_person_hotspot:
                type_counts['missing_person'] += 1
                crime_type_counts['missing_person'] += 1
            else:
                type_counts['crime'] += 1
                crime_type = hotspot.crime_type or 'unknown'
                crime_type_counts[crime_type] += 1

        return {
            'total_hotspots': len(hotspots),
            'total_incidents': total_incidents,
            'avg_incidents_per_hotspot': total_incidents / len(hotspots),
            'by_risk_level': dict(risk_level_counts),
            'by_type': dict(type_counts),
            'by_crime_type': dict(crime_type_counts)  # ✅ NEW: breakdown by specific crime types
        }