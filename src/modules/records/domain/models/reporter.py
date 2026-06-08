from src.modules.records.domain.models.enums import RelationshipType
from src.shared.data.base.model import BaseModel
from src.shared.data.database import db


class Reporter(BaseModel):
    """Model for person who reports a missing person"""
    __tablename__ = 'reporters'

    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    relationship = db.Column(db.Enum(RelationshipType), nullable=False)  # Relation to missing person
    phone_number = db.Column(db.String(20), nullable=False, index=True)
    email = db.Column(db.String(100), nullable=True)

    # Use Location relationship
    address_id = db.Column(db.String(36), db.ForeignKey('locations.id'), nullable=True)
    address = db.relationship('Location')

    missing_person_id = db.Column(db.String(36), db.ForeignKey('missing_persons.id'),
                                  nullable=False, index=True)
    missing_person = db.relationship('MissingPerson', back_populates='reporter')

    # Track who recorded this reporter information
    recorded_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    recorded_by_user = db.relationship('User', foreign_keys=[recorded_by])

