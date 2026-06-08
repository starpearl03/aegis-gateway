from src.modules.records.domain.models.enums import Gender
from src.shared.data.base.model import BaseModel
from src.shared.data.database import db


class Person(BaseModel):
    """Base model for any person in the system"""
    __tablename__ = 'persons'

    first_name = db.Column(db.String(100), nullable=False, index=True)
    last_name = db.Column(db.String(100), nullable=False, index=True)
    date_of_birth = db.Column(db.Date, nullable=True, index=True)
    gender = db.Column(db.Enum(Gender), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True, index=True)
    email = db.Column(db.String(100), nullable=True, index=True)
    national_id = db.Column(db.String(50), nullable=True, unique=True, index=True)

    # Physical characteristics
    height = db.Column(db.Float, nullable=True)  # in cm
    weight = db.Column(db.Float, nullable=True)  # in kg
    hair_color = db.Column(db.String(50), nullable=True)
    eye_color = db.Column(db.String(50), nullable=True)
    skin_tone = db.Column(db.String(50), nullable=True)
    distinctive_features = db.Column(db.Text, nullable=True)

    # Address as relationship to Location
    address_id = db.Column(db.String(36), db.ForeignKey('locations.id'), nullable=True)
    address = db.relationship('Location', foreign_keys=[address_id])

    description = db.Column(db.Text, nullable=True)

    # Track who created/modified this person record
    created_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    updated_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)

    # Relationships
    images = db.relationship('PersonImage', back_populates='person', lazy='dynamic',
                             cascade="all, delete-orphan")

    # Polymorphic identity for inheritance
    type = db.Column(db.String(50))
    __mapper_args__ = {
        'polymorphic_identity': 'person',
        'polymorphic_on': type
    }