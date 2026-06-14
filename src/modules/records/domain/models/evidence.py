# src/modules/records/domain/models/evidence.py
from src.modules.records.domain.models.enums import EvidenceType
from src.shared.data.base.model import BaseModel
from src.shared.data.database import db
from pgvector.sqlalchemy import Vector

class EvidenceFaceVector(BaseModel):
    """
    Model for storing face vectors detected in evidence.
    Each face detected in an image/video gets its own record.
    """
    __tablename__ = 'evidence_face_vectors'

    # The actual face embedding vector (512-dimensional)
    vector = db.Column(Vector(512), nullable=False)

    # Foreign key to evidence
    evidence_id = db.Column(
        db.String(36),
        db.ForeignKey('evidence.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Relationships
    evidence = db.relationship('Evidence', back_populates='face_vectors')

    __table_args__ = (
        db.Index('idx_face_vector_evidence', 'evidence_id'),
    )

    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<EvidenceFaceVector(id={self.id}, evidence_id={self.evidence_id})>"


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

    # Foreign key
    crime_id = db.Column(db.String(36), db.ForeignKey('crimes.id'), nullable=False, index=True)

    # Relationships
    crime = db.relationship('Crime', back_populates='evidence')
    face_vectors = db.relationship('EvidenceFaceVector', back_populates='evidence', cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_evidence_type', 'type'),
    )