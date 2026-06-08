from src.modules.records.domain.models.enums import MissingPersonStatus
from src.shared.data.base.model import BaseModel
from src.shared.data.database import db


class MissingPersonStatusHistory(BaseModel):
    """Track status changes for missing persons"""
    __tablename__ = 'missing_person_status_history'

    missing_person_id = db.Column(db.String(36), db.ForeignKey('missing_persons.id'),
                                  nullable=False, index=True)
    old_status = db.Column(db.Enum(MissingPersonStatus), nullable=True)
    new_status = db.Column(db.Enum(MissingPersonStatus), nullable=False)

    # Track who made the status change
    changed_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    changed_by_user = db.relationship('User', foreign_keys=[changed_by])

    notes = db.Column(db.Text, nullable=True)

    missing_person = db.relationship('MissingPerson', back_populates='status_history')
