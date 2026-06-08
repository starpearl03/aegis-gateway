from src.modules.records.domain.models.enums import MissingPersonStatus
from src.modules.records.domain.models.person import Person
from src.shared.data.database import db


class MissingPerson(Person):
    """Model for missing person records"""
    __tablename__ = 'missing_persons'

    id = db.Column(db.String(36), db.ForeignKey('persons.id'), primary_key=True)
    status = db.Column(db.Enum(MissingPersonStatus), default=MissingPersonStatus.MISSING,
                       nullable=False, index=True)

    last_seen_date = db.Column(db.DateTime, nullable=False, index=True)

    # Use Location relationship instead of string
    last_seen_location_id = db.Column(db.String(36), db.ForeignKey('locations.id'), nullable=False)
    last_seen_location = db.relationship('Location', foreign_keys=[last_seen_location_id])

    circumstances = db.Column(db.Text, nullable=True)  # Details of disappearance

    # Found information
    found_date = db.Column(db.DateTime, nullable=True, index=True)
    found_location_id = db.Column(db.String(36), db.ForeignKey('locations.id'), nullable=True)
    found_location = db.relationship('Location', foreign_keys=[found_location_id])
    found_condition = db.Column(db.Text, nullable=True)

    # Track officer handling the case
    assigned_officer_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    assigned_officer = db.relationship('User', foreign_keys=[assigned_officer_id])

    # Relationships
    reporter = db.relationship('Reporter', back_populates='missing_person',
                               uselist=False, cascade="all, delete-orphan")
    status_history = db.relationship('MissingPersonStatusHistory', back_populates='missing_person',
                                     cascade="all, delete-orphan")

    __mapper_args__ = {
        'polymorphic_identity': 'missing_person',
    }

    __table_args__ = (
        db.Index('idx_missing_status_date', 'status', 'last_seen_date'),
    )