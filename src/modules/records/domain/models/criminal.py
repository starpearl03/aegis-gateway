from src.modules.records.domain.models.enums import ThreatLevel
from src.modules.records.domain.models.person import Person
from src.shared.data.database import db


class Criminal(Person):
    """Model for criminal records"""
    __tablename__ = 'criminals'

    id = db.Column(db.String(36), db.ForeignKey('persons.id'), primary_key=True)
    alias = db.Column(db.String(100), nullable=True, index=True)
    is_wanted = db.Column(db.Boolean, default=False, index=True)
    priority_level = db.Column(db.Integer, default=0, index=True)  # 0-5 scale
    gang_affiliation = db.Column(db.String(100), nullable=True)

    # Risk assessment
    threat_level = db.Column(db.Enum(ThreatLevel), nullable=True)

    # Relationships
    crimes = db.relationship('Crime', back_populates='criminal', lazy='dynamic',
                             cascade="all, delete-orphan")

    __mapper_args__ = {
        'polymorphic_identity': 'criminal',
    }

    __table_args__ = (
        db.Index('idx_criminal_wanted_priority', 'is_wanted', 'priority_level'),
    )
