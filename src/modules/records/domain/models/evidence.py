from pgvector import Vector

from src.modules.records.domain.models.enums import EvidenceType
from src.shared.data.base.model import BaseModel
from src.shared.data.database import db


class Evidence(BaseModel):
    """Model for evidence related to crimes"""
    __tablename__ = 'evidence'

    description = db.Column(db.Text, nullable=False)
    type = db.Column(db.Enum(EvidenceType), nullable=False, index=True)
    file_path = db.Column(db.String(255), nullable=True)

    # Chain of custody - who collected the evidence
    collected_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    collected_by_user = db.relationship('User', foreign_keys=[collected_by])
    collected_date = db.Column(db.DateTime, nullable=True)
    storage_location = db.Column(db.String(255), nullable=True)

    # For video/image evidence with facial recognition
    # Store multiple face vectors if multiple faces detected
    face_vectors = db.Column(db.ARRAY(Vector(512)), nullable=True)

    # Foreign key
    crime_id = db.Column(db.String(36), db.ForeignKey('crimes.id'), nullable=False, index=True)

    # Relationships
    crime = db.relationship('Crime', back_populates='evidence')

    __table_args__ = (
        db.Index('idx_evidence_type', 'type'),
    )