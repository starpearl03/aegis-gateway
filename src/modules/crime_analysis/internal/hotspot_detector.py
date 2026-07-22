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

        Args:
            crimes: List of Crime entities
            missing_persons: List of MissingPerson entities

        Returns:
            List of HotspotData objects representing detected hotspots
        """
        logger.info(f"Starting hotspot detection with radius={self.radius_km}km, "
                   f"min_incidents={self.min_incidents}")
        logger.info(f"Input: {len(crimes)} crimes, {len(missing_persons)} missing persons")

        # Extract location data from crimes and missing persons
        crime_locations = self._extract_crime_locations(crimes)
        missing_locations = self._extract_missing_person_locations(missing_persons)

        # Combine all locations
        all_locations = crime_locations + missing_locations

        if not all_locations:
            logger.warning("No locations found for clustering")
            return []

        logger.info(f"Total locations to cluster: {len(all_locations)}")

        # Perform clustering
        clusters = self._cluster_locations(all_locations)

        # Build hotspots from clusters
        hotspots = self._build_hotspots(clusters, all_locations)

        logger.info(f"Detected {len(hotspots)} hotspots")
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

        logger.info(f"Clustering complete: {num_clusters} clusters, {num_noise} noise points")

        return cluster_labels

    def _build_hotspots(
            self,
            cluster_labels: np.ndarray,
            locations: List[Dict[str, Any]]
    ) -> List[HotspotData]:
        """
        Build hotspot data structures from clusters.

        Args:
            cluster_labels: Array of cluster labels from DBSCAN
            locations: List of location dictionaries

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
            hotspot = self._create_hotspot_from_cluster(cluster_id, cluster_locations)
            hotspots.append(hotspot)

        # Sort hotspots by incident count (descending)
        hotspots.sort(key=lambda h: h.incident_count, reverse=True)

        return hotspots

    def _create_hotspot_from_cluster(
            self,
            cluster_id: int,
            cluster_locations: List[Dict[str, Any]]
    ) -> HotspotData:
        """
        Create a HotspotData object from a cluster of locations.

        Args:
            cluster_id: Cluster identifier
            cluster_locations: List of locations in this cluster

        Returns:
            HotspotData object
        """
        # Calculate centroid (average lat/lng) and convert to native float
        avg_lat = float(np.mean([loc['latitude'] for loc in cluster_locations]))
        avg_lng = float(np.mean([loc['longitude'] for loc in cluster_locations]))

        # Find the most representative location_id (most common or closest to centroid)
        location_id = self._get_representative_location_id(cluster_locations, avg_lat, avg_lng)

        # Determine if it's primarily a missing person hotspot
        missing_count = sum(1 for loc in cluster_locations if loc['type'] == 'missing_person')
        crime_count = len(cluster_locations) - missing_count
        is_missing_person_hotspot = missing_count > crime_count

        # Determine predominant crime type (if applicable)
        crime_type = None
        if not is_missing_person_hotspot:
            crime_types = [loc['crime_type'] for loc in cluster_locations
                           if loc['crime_type'] is not None]
            if crime_types:
                crime_type = max(set(crime_types), key=crime_types.count)

        # Calculate risk level based on incident count
        incident_count = len(cluster_locations)
        risk_level = self._calculate_risk_level(incident_count, is_missing_person_hotspot)

        return HotspotData(
            location_id=location_id,
            latitude=avg_lat,
            longitude=avg_lng,
            incident_count=incident_count,
            crime_type=crime_type,
            is_missing_person_hotspot=is_missing_person_hotspot,
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
                'by_type': {}
            }

        total_incidents = sum(h.incident_count for h in hotspots)

        risk_level_counts = defaultdict(int)
        type_counts = defaultdict(int)

        for hotspot in hotspots:
            risk_level_counts[hotspot.risk_level] += 1
            type_key = 'missing_person' if hotspot.is_missing_person_hotspot else 'crime'
            type_counts[type_key] += 1

        return {
            'total_hotspots': len(hotspots),
            'total_incidents': total_incidents,
            'avg_incidents_per_hotspot': total_incidents / len(hotspots),
            'by_risk_level': dict(risk_level_counts),
            'by_type': dict(type_counts)
        }