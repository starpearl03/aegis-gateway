from enum import Enum

from src.shared.data.base.model import BaseModel
from src.shared.data.database import db
from werkzeug.security import generate_password_hash, check_password_hash

class UserRole(Enum):
    """User role enumeration."""
    ADMIN = 'admin'


class User(BaseModel):
    """
    User model for authentication and profile management.
    """
    __tablename__ = 'users'

    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.ADMIN)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def set_password(self, password: str) -> None:
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify the provided password against the hash."""
        return check_password_hash(self.password_hash, password)

    def to_dict(self, exclude: list = None) -> dict:
        """Override to handle password exclusion, enum serialization, and datetime conversion."""
        exclude = exclude or []
        if 'password_hash' not in exclude:
            exclude.append('password_hash')

        data = super().to_dict(exclude=exclude)

        # Handle enum serialization
        if 'role' in data:
            data['role'] = self.role.value if hasattr(self.role, 'value') else self.role

        # Handle datetime serialization
        if 'created_at' in data and self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if 'updated_at' in data and self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()

        return data

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"