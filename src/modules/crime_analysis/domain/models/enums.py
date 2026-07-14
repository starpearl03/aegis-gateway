# src/modules/analysis/domain/models/enums.py
from enum import Enum


class RiskLevel(Enum):
    """Risk level for crime hotspots"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TrendCategory(Enum):
    """Category of crime trend"""
    CRIME = "crime"
    MISSING_PERSON = "missing_person"
    COMBINED = "combined"


class SeverityLevel(Enum):
    """Severity level for trends"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PriorityLevel(Enum):
    """Priority level for recommendations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class BroadcastStatus(Enum):
    """Status of alert broadcast"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"