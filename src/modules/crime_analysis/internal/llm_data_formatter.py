# src/modules/analysis/internal/llm_data_formatter.py
from typing import List, Dict, Any
from datetime import datetime
from collections import Counter

from src.modules.crime_analysis.internal.hotspot_detector import HotspotData
from src.modules.records.domain.models.crime import Crime
from src.modules.records.domain.models.missing_person import MissingPerson


class LLMDataFormatter:
    """
    Utility class for formatting crime and missing person data for LLM analysis.
    Cleans data, removes noise, and structures it for optimal LLM processing.
    """

    def prepare_analysis_prompt(
            self,
            crimes: List[Crime],
            missing_persons: List[MissingPerson],
            hotspots: List[HotspotData],
            start_date: datetime,
            end_date: datetime
    ) -> str:
        """
        Prepare a comprehensive prompt for LLM analysis with pre-calculated hotspots.

        Args:
            crimes: List of Crime entities
            missing_persons: List of MissingPerson entities
            hotspots: List of pre-calculated HotspotData objects
            start_date: Analysis period start
            end_date: Analysis period end

        Returns:
            Formatted prompt string ready for LLM
        """
        # Aggregate data
        crime_summary = self._aggregate_crime_data(crimes)
        missing_person_summary = self._aggregate_missing_person_data(missing_persons)
        hotspot_summary = self._format_hotspots_for_llm(hotspots)

        # Build the prompt
        return self._build_prompt(
            crime_summary,
            missing_person_summary,
            hotspot_summary,
            start_date,
            end_date
        )

    def _aggregate_crime_data(self, crimes: List[Crime]) -> Dict[str, Any]:
        """Aggregate and summarize crime data for LLM consumption."""
        if not crimes:
            return self._empty_crime_summary()

        # Count crimes by type
        crime_types = Counter(crime.crime_type for crime in crimes)

        # Count crimes by location with details
        location_counts = Counter(crime.location_id for crime in crimes if crime.location_id)
        location_details = self._extract_location_details(crimes, location_counts)

        # Count crimes by status
        status_counts = Counter(crime.status.value for crime in crimes)

        # Temporal patterns
        temporal_patterns = self._extract_temporal_patterns(crimes)

        return {
            'total_count': len(crimes),
            'by_type': dict(crime_types),
            'by_location': location_details,
            'by_status': dict(status_counts),
            'temporal_patterns': temporal_patterns
        }

    def _aggregate_missing_person_data(self, missing_persons: List[MissingPerson]) -> Dict[str, Any]:
        """Aggregate and summarize missing person data for LLM consumption."""
        if not missing_persons:
            return self._empty_missing_person_summary()

        # Count by status
        status_counts = Counter(mp.status.value for mp in missing_persons)

        # Count by last seen location
        location_counts = Counter(
            mp.last_seen_location_id for mp in missing_persons if mp.last_seen_location_id
        )
        location_details = self._extract_location_details_missing(missing_persons, location_counts)

        # Demographics and temporal patterns
        demographics = self._extract_demographics(missing_persons)
        temporal_patterns = self._extract_temporal_patterns_missing(missing_persons)

        return {
            'total_count': len(missing_persons),
            'by_status': dict(status_counts),
            'by_location': location_details,
            'by_demographics': demographics,
            'temporal_patterns': temporal_patterns
        }

    def _format_hotspots_for_llm(self, hotspots: List[HotspotData]) -> str:
        """
        Format pre-calculated hotspots for LLM prompt.

        Args:
            hotspots: List of HotspotData objects

        Returns:
            Formatted string describing hotspots
        """
        if not hotspots:
            return "No hotspots detected in this analysis period."

        formatted_hotspots = []
        for idx, hotspot in enumerate(hotspots, 1):
            hotspot_type = "Missing Person Hotspot" if hotspot.is_missing_person_hotspot else "Crime Hotspot"
            crime_info = f" (Primary Type: {hotspot.crime_type})" if hotspot.crime_type else ""

            hotspot_str = (
                f"{idx}. {hotspot_type}{crime_info}\n"
                f"   - Location ID: {hotspot.location_id}\n"
                f"   - Coordinates: [{hotspot.latitude:.4f}, {hotspot.longitude:.4f}]\n"
                f"   - Incident Count: {hotspot.incident_count}\n"
                f"   - Risk Level: {hotspot.risk_level.upper()}\n"
                f"   - Cluster ID: {hotspot.cluster_id}"
            )
            formatted_hotspots.append(hotspot_str)

        return "\n\n".join(formatted_hotspots)

    def _extract_location_details(self, crimes: List[Crime], location_counts: Counter) -> Dict[str, Any]:
        """Extract location details from crimes."""
        location_details = {}
        seen = set()

        for crime in crimes:
            if crime.location_id and crime.location_id not in seen and crime.location:
                seen.add(crime.location_id)
                location_details[crime.location_id] = {
                    'address': crime.location.address or 'Unknown',
                    'city': crime.location.city or 'Unknown',
                    'latitude': float(crime.location.latitude),
                    'longitude': float(crime.location.longitude),
                    'count': location_counts[crime.location_id]
                }

        return location_details

    def _extract_location_details_missing(self, missing_persons: List[MissingPerson],
                                          location_counts: Counter) -> Dict[str, Any]:
        """Extract location details from missing persons."""
        location_details = {}
        seen = set()

        for mp in missing_persons:
            if mp.last_seen_location_id and mp.last_seen_location_id not in seen and mp.last_seen_location:
                seen.add(mp.last_seen_location_id)
                location_details[mp.last_seen_location_id] = {
                    'address': mp.last_seen_location.address or 'Unknown',
                    'city': mp.last_seen_location.city or 'Unknown',
                    'latitude': float(mp.last_seen_location.latitude),
                    'longitude': float(mp.last_seen_location.longitude),
                    'count': location_counts[mp.last_seen_location_id]
                }

        return location_details

    def _extract_temporal_patterns(self, crimes: List[Crime]) -> Dict[str, Any]:
        """Extract temporal patterns from crimes."""
        day_of_week = Counter()
        hour_of_day = Counter()

        for crime in crimes:
            if crime.date_committed:
                day_of_week[crime.date_committed.strftime('%A')] += 1
                hour_of_day[crime.date_committed.hour] += 1

        return {
            'by_day_of_week': dict(day_of_week),
            'by_hour_of_day': dict(hour_of_day)
        }

    def _extract_temporal_patterns_missing(self, missing_persons: List[MissingPerson]) -> Dict[str, Any]:
        """Extract temporal patterns from missing persons."""
        day_of_week = Counter()
        hour_of_day = Counter()

        for mp in missing_persons:
            if mp.last_seen_date:
                day_of_week[mp.last_seen_date.strftime('%A')] += 1
                hour_of_day[mp.last_seen_date.hour] += 1

        return {
            'by_day_of_week': dict(day_of_week),
            'by_hour_of_day': dict(hour_of_day)
        }

    def _extract_demographics(self, missing_persons: List[MissingPerson]) -> Dict[str, Any]:
        """Extract demographic patterns from missing persons."""
        gender_counts = Counter()
        age_groups = Counter()

        for mp in missing_persons:
            if mp.gender:
                gender_counts[mp.gender.value] += 1

            if mp.date_of_birth:
                age = self._calculate_age(mp.date_of_birth)
                age_group = self._get_age_group(age)
                age_groups[age_group] += 1

        return {
            'by_gender': dict(gender_counts),
            'by_age_group': dict(age_groups)
        }

    def _calculate_age(self, date_of_birth) -> int:
        """Calculate age from date of birth."""
        today = datetime.now().date()
        return today.year - date_of_birth.year - (
                (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
        )

    def _get_age_group(self, age: int) -> str:
        """Categorize age into groups."""
        if age < 13:
            return 'Child (0-12)'
        elif age < 18:
            return 'Teen (13-17)'
        elif age < 25:
            return 'Young Adult (18-24)'
        elif age < 35:
            return 'Adult (25-34)'
        elif age < 50:
            return 'Middle Age (35-49)'
        elif age < 65:
            return 'Senior (50-64)'
        else:
            return 'Elderly (65+)'

    def _build_prompt(
            self,
            crime_summary: Dict[str, Any],
            missing_person_summary: Dict[str, Any],
            hotspot_summary: str,
            start_date: datetime,
            end_date: datetime
    ) -> str:
        """Build the final prompt for LLM analysis with pre-calculated hotspots."""

        prompt = f"""# ROLE: Senior Crime Intelligence Analyst

You are a seasoned detective turned crime analyst with 20+ years of experience in law enforcement. Your analytical mind is trained to distinguish between:
- **Normal criminal activity** (isolated incidents that regular police patrols can handle)
- **Concerning patterns** (serial crimes, targeted attacks, or organized criminal activity requiring investigation)
- **Critical threats** (emerging dangerous trends requiring immediate public alerts and enhanced police deployment)

## YOUR ANALYTICAL PHILOSOPHY

**Be PRECISE and EVIDENCE-BASED:**
- Don't create panic over isolated incidents or normal crime fluctuation
- Only flag patterns that show clear evidence of systematic or serial activity
- Distinguish between correlation and causation
- Focus on actionable intelligence, not speculation

**Think like a detective:**
- What story does the data tell?
- Are incidents related or coincidental?
- Is there a modus operandi (MO) or pattern?
- Who is vulnerable and why?
- What preventive measures would actually work?

---

## ANALYSIS PERIOD
- **Start Date:** {start_date.strftime('%Y-%m-%d %H:%M:%S')}
- **End Date:** {end_date.strftime('%Y-%m-%d %H:%M:%S')}

---

## CRIME DATA SUMMARY

### Overall Statistics
- **Total Crimes:** {crime_summary['total_count']}
- **Crimes by Type:** {self._format_dict(crime_summary['by_type'])}
- **Crimes by Status:** {self._format_dict(crime_summary['by_status'])}

### Geographic Distribution
**Top Crime Locations:**
{self._format_location_data(crime_summary['by_location'])}

### Temporal Intelligence
- **By Day of Week:** {self._format_dict(crime_summary['temporal_patterns'].get('by_day_of_week', {}))}
- **By Hour of Day:** {self._format_dict(crime_summary['temporal_patterns'].get('by_hour_of_day', {}))}

---

## MISSING PERSONS DATA SUMMARY

### Overall Statistics
- **Total Missing Persons:** {missing_person_summary['total_count']}
- **By Status:** {self._format_dict(missing_person_summary['by_status'])}

### Geographic Distribution
**Top Missing Person Locations:**
{self._format_location_data(missing_person_summary['by_location'])}

### Demographics
- **By Gender:** {self._format_dict(missing_person_summary['by_demographics'].get('by_gender', {}))}
- **By Age Group:** {self._format_dict(missing_person_summary['by_demographics'].get('by_age_group', {}))}

### Temporal Intelligence
- **By Day of Week:** {self._format_dict(missing_person_summary['temporal_patterns'].get('by_day_of_week', {}))}
- **By Hour of Day:** {self._format_dict(missing_person_summary['temporal_patterns'].get('by_hour_of_day', {}))}

---

## PRE-IDENTIFIED HOTSPOTS (Geospatial Clustering Analysis)

The following hotspots have been identified using DBSCAN clustering algorithm (2km radius):

{hotspot_summary}

**Note:** These are geographically clustered incident locations. Your job is to determine if they represent concerning patterns or just normal crime distribution.

---

## YOUR ANALYTICAL TASK

Analyze the data with the precision of a seasoned detective. Provide a JSON response following this structure:

### CRITICAL GUIDELINES:

**1. DISTINGUISHING NORMAL vs. CONCERNING ACTIVITY:**

**🟢 NORMAL (No Special Action Needed):**
- Isolated incidents spread across time and location
- Low incident count in hotspots (3-5 incidents over analysis period)
- Random crime types with no pattern
- Expected crime for area demographics/economics
- **Response:** Acknowledge as baseline crime, recommend standard patrols

**🟡 CONCERNING (Investigation Needed):**
- Repeated crime type in specific location (possible serial offender)
- Multiple missing persons with similar demographics from same area
- Emerging temporal patterns (all incidents on weekends, late night)
- Escalating severity over time
- **Response:** Recommend targeted investigation, increased patrols during risk hours

**🔴 CRITICAL (Immediate Action Required):**
- Serial crimes with clear MO (method of operation)
- Multiple missing persons of same demographic (potential predator)
- Organized crime indicators (coordinated activities)
- High-risk vulnerable population targeted (children, elderly)
- Dangerous locations requiring public alerts
- **Response:** Urgent police deployment, public safety alerts, community warnings

**2. EVIDENCE-BASED REASONING:**
- Only identify trends when there's clear supporting evidence
- State confidence level (High/Medium/Low) based on data strength
- Distinguish between "might be" and "definitely is"
- If data is insufficient, say so clearly

**3. ACTIONABLE RECOMMENDATIONS:**
- Be specific: "Deploy 2 patrol units to [location] between 10PM-2AM on Friday-Saturday" ✅
- Not vague: "Increase police presence" ❌
- Focus on prevention, not just reaction
- Consider resource constraints (don't recommend unrealistic solutions)

---

## JSON RESPONSE FORMAT

{{
    "summary": "Write a 2-3 paragraph executive summary as if briefing the police chief. Start with the bottom line: 'This analysis period shows [normal baseline crime / concerning patterns / critical threats requiring immediate action].' Then explain WHY, citing specific evidence from the data. Be honest about data limitations. Don't create alarm where none is warranted, but don't downplay genuine threats.",

    "trends": [
        {{
            "hotspot_id": null,
            "trend_category": "crime" | "missing_person" | "combined",
            "crime_type": "specific crime type or null",
            "description": "Describe the pattern with detective-level detail. Example: 'Serial burglaries showing consistent MO: all residential, weekday mornings 9AM-11AM, targeting homes near [location]. Victims report similar suspect description.' Include: What pattern exists? What's the evidence? Why is it concerning (or not)? What's the likely explanation?",
            "affected_demographic": "Be specific: 'Young women aged 18-25' not just 'youth'. Include null if no specific demographic.",
            "time_pattern": "Precise temporal patterns: 'Friday-Saturday nights, 11PM-3AM' or 'Weekday mornings during school hours' or null if no pattern",
            "severity": "low" | "medium" | "high"
        }}
    ],

    "recommendations": [
        {{
            "hotspot_id": null,
            "recommendation_text": "Provide tactical, implementable recommendations. Format: [ACTION] + [SPECIFIC LOCATION/TIME] + [REASONING]. Examples:\\n\\n✅ GOOD: 'Deploy undercover units to [coordinates] disguised as maintenance workers on weekdays 9AM-11AM. Pattern shows burglar strikes when area appears empty. Install temporary surveillance cameras at entry points.'\\n\\n✅ GOOD: 'No special deployment needed. Incident distribution shows normal baseline crime for this urban area. Continue standard patrol rotation.'\\n\\n❌ BAD: 'Increase police presence and surveillance.'\\n\\n❌ BAD: 'Deploy more officers to high-crime areas.'",
            "priority": "low" | "medium" | "high" | "urgent"
        }}
    ]
}}

---

## PRIORITY LEVEL DEFINITIONS

- **LOW:** Normal crime, standard response adequate, routine monitoring
- **MEDIUM:** Emerging pattern worth watching, schedule investigation, minor patrol adjustment
- **HIGH:** Clear concerning pattern, immediate investigation needed, targeted deployment
- **URGENT:** Active serial activity or imminent public danger, emergency response, public alert

---

## TECHNICAL REQUIREMENTS

1. **DO NOT create or generate hotspots** - they are already provided above
2. **DO NOT invent UUIDs or IDs** - always set hotspot_id to null
3. **Return ONLY valid JSON** - no markdown (```json), no code blocks, no explanatory text
4. **Base analysis ONLY on provided data** - no external information or assumptions
5. **Be honest about data limitations** - if sample size is too small for conclusions, say so
6. **Avoid false positives** - better to miss a weak pattern than create false alarm

---

## OUTPUT FORMAT

Return raw JSON object only. No markdown formatting. No explanations outside JSON.

Begin your analysis now.
"""
        return prompt

    def _format_dict(self, data: Dict[str, Any]) -> str:
        """Format dictionary for readable prompt output."""
        if not data:
            return "No data available"
        return ", ".join([f"{k}: {v}" for k, v in sorted(data.items(), key=lambda x: x[1], reverse=True)])

    def _format_location_data(self, location_data: Dict[str, Any]) -> str:
        """Format location data for readable prompt output."""
        if not location_data:
            return "No location data available"

        # Sort by count (top 10)
        sorted_locations = sorted(
            location_data.items(),
            key=lambda x: x[1].get('count', 0),
            reverse=True
        )[:10]

        formatted = []
        for loc_id, data in sorted_locations:
            formatted.append(
                f"  - ID: {loc_id}\n"
                f"    Address: {data.get('address', 'Unknown')} ({data.get('city', 'Unknown')})\n"
                f"    Incidents: {data.get('count', 0)}\n"
                f"    Coordinates: [{data.get('latitude', 0):.4f}, {data.get('longitude', 0):.4f}]"
            )

        return "\n".join(formatted) if formatted else "No location data available"

    @staticmethod
    def _empty_crime_summary() -> Dict[str, Any]:
        """Return empty crime summary structure."""
        return {
            'total_count': 0,
            'by_type': {},
            'by_location': {},
            'by_status': {},
            'temporal_patterns': {'by_day_of_week': {}, 'by_hour_of_day': {}}
        }

    @staticmethod
    def _empty_missing_person_summary() -> Dict[str, Any]:
        """Return empty missing person summary structure."""
        return {
            'total_count': 0,
            'by_status': {},
            'by_location': {},
            'by_demographics': {'by_gender': {}, 'by_age_group': {}},
            'temporal_patterns': {'by_day_of_week': {}, 'by_hour_of_day': {}}
        }