# Shared Enums
from enum import Enum


class MissingPersonStatus(Enum):
    """Status options for missing persons"""
    MISSING = "missing"
    LOCATED_ALIVE = "located_alive"
    LOCATED_DECEASED = "located_deceased"
    INVESTIGATION_CLOSED = "investigation_closed"

class CrimeStatus(Enum):
    """Status options for crime cases"""
    OPEN = "open"
    UNDER_INVESTIGATION = "under_investigation"
    SOLVED = "solved"
    CLOSED_UNSOLVED = "closed_unsolved"
    PENDING_TRIAL = "pending_trial"
    COLD_CASE = "cold_case"


class PunishmentType(Enum):
    """Types of punishments that can be given"""
    JAIL = "jail"
    PRISON = "prison"
    FINE = "fine"
    PROBATION = "probation"
    COMMUNITY_SERVICE = "community_service"
    SUSPENDED_SENTENCE = "suspended_sentence"
    ACQUITTED = "acquitted"
    DEATH_PENALTY = "death_penalty"


class PunishmentStatus(Enum):
    """Status options for punishments"""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    OVERDUE = "overdue"
    PARTIALLY_PAID = "partially_paid"


class ThreatLevel(Enum):
    """Threat level assessment for criminals"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceType(Enum):
    """Types of evidence that can be collected"""
    PHOTOGRAPH = "photograph"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    PHYSICAL = "physical"
    DIGITAL = "digital"
    FORENSIC = "forensic"
    WITNESS_STATEMENT = "witness_statement"
    DNA = "dna"
    FINGERPRINT = "fingerprint"


class Gender(Enum):
    """Gender options"""
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class RelationshipType(Enum):
    """Relationship types for reporters to missing persons"""
    PARENT = "parent"
    SPOUSE = "spouse"
    SIBLING = "sibling"
    CHILD = "child"
    RELATIVE = "relative"
    FRIEND = "friend"
    NEIGHBOR = "neighbor"
    COLLEAGUE = "colleague"
    GUARDIAN = "guardian"
    OTHER = "other"