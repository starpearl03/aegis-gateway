from src.shared.data.base.model import BaseModel
from src.shared.data.database import db


class CrimeVictim(BaseModel):
    """Model for crime victims (proper relationship)"""
    __tablename__ = 'crime_victims'

    crime_id = db.Column(db.String(36), db.ForeignKey('crimes.id'), nullable=False, index=True)
    person_id = db.Column(db.String(36), db.ForeignKey('persons.id'), nullable=False, index=True)

    injury_description = db.Column(db.Text, nullable=True)
    medical_report_path = db.Column(db.String(255), nullable=True)

    crime = db.relationship('Crime', back_populates='victims')
    person = db.relationship('Person')

    # Track who recorded this victim information
    recorded_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    recorded_by_user = db.relationship('User', foreign_keys=[recorded_by])

    __table_args__ = (
        db.UniqueConstraint('crime_id', 'person_id', name='uq_crime_victim'),
    )