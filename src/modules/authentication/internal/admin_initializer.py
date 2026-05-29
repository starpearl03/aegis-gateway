# File: src/modules/authentication/internal/admin_initializer.py

from typing import Optional
import logging

from src.modules.authentication.domain.models.user import User, UserRole
from src.modules.authentication.domain.repositories.user_repository import UserRepository
from src.modules.authentication.domain.services.auth_service import AuthenticationService
from src.modules.authentication.presentation.dtos.authentication import RegisterRequest, RegisterResponse
from src.shared.configs.exceptions.exceptions import AlreadyExistsException, ValidationException

logger = logging.getLogger(__name__)


class AdminInitializer:
    """Service to initialize default admin user on system startup."""

    # Default admin credentials
    DEFAULT_ADMIN_EMAIL = "admin@gmail.com"
    DEFAULT_ADMIN_PASSWORD = "@Qwerty12"
    DEFAULT_ADMIN_FIRST_NAME = "System"
    DEFAULT_ADMIN_LAST_NAME = "Administrator"

    @classmethod
    def create_default_admin(cls) -> Optional[RegisterResponse]:
        """
        Create default admin user if it doesn't exist.

        Returns:
            RegisterResponse object if created, None if already exists
        """
        user_repository = UserRepository()
        auth_service = AuthenticationService()

        # Check if admin already exists
        existing_admin = user_repository.find_by_email(cls.DEFAULT_ADMIN_EMAIL)

        if existing_admin:
            logger.info(f"Admin user already exists: {cls.DEFAULT_ADMIN_EMAIL}")
            return None

        try:
            # Create registration request
            register_request = RegisterRequest(
                email=cls.DEFAULT_ADMIN_EMAIL,
                password=cls.DEFAULT_ADMIN_PASSWORD,
                first_name=cls.DEFAULT_ADMIN_FIRST_NAME,
                last_name=cls.DEFAULT_ADMIN_LAST_NAME,
                role=UserRole.ADMIN.value
            )

            # Register admin user using AuthenticationService
            response = auth_service.register(register_request)

            logger.info("=" * 60)
            logger.info("DEFAULT ADMIN USER CREATED SUCCESSFULLY")
            logger.info("=" * 60)
            logger.info(f"Email: {response.email}")
            logger.info(f"Name: {response.first_name} {response.last_name}")
            logger.info(f"Role: {response.role}")
            logger.info(f"Password: {cls.DEFAULT_ADMIN_PASSWORD}")
            logger.warning("IMPORTANT: Please change the default admin password immediately!")
            logger.info("=" * 60)

            return response

        except AlreadyExistsException as e:
            logger.warning(f"Admin user already exists: {str(e)}")
            return None

        except ValidationException as e:
            logger.error(f"Validation error creating admin user: {str(e)}")
            raise

        except Exception as e:
            logger.error(f"Failed to create default admin user: {str(e)}")
            raise

    @classmethod
    def initialize(cls) -> None:
        """Initialize default admin user on system startup."""
        logger.info("Starting admin initialization...")
        cls.create_default_admin()
        logger.info("Admin initialization complete")