from src.modules.authentication.domain.models.user import User, UserRole
from src.modules.authentication.domain.repositories.user_repository import UserRepository
from src.modules.authentication.presentation.dtos.authentication import RegisterRequest, RegisterResponse, LoginRequest, \
    LoginResponse, LogoutRequest, LogoutResponse
from src.shared.configs.exceptions.exceptions import AlreadyExistsException, ValidationException, UnauthorizedException, \
    NotFoundException


class AuthenticationService:
    """
    Service for handling authentication operations.
    Provides methods for user registration, login, and logout.
    """

    def __init__(self):
        self.user_repository = UserRepository()

    def register(self, request: RegisterRequest) -> RegisterResponse:
        """
        Register a new user.

        Args:
            request: RegisterRequest DTO containing registration data (already validated)

        Returns:
            RegisterResponse DTO with user data

        Raises:
            ValidationException: If validation fails or user creation fails
            AlreadyExistsException: If email already exists
        """
        # Validation happens automatically in RegisterRequest.__post_init__

        # Check if email already exists
        if self.user_repository.email_exists(request.email):
            raise AlreadyExistsException(f"Email {request.email} already exists")

        # Parse role
        role = UserRole.ADMIN
        if request.role:
            try:
                role = UserRole(request.role)
            except ValueError:
                raise ValidationException(f"Invalid role: {request.role}")

        try:
            # Create user instance
            user = User(
                email=request.email,
                first_name=request.first_name,
                last_name=request.last_name,
                role=role,
                is_active=True
            )
            user.set_password(request.password)

            # Save to database
            created_user = self.user_repository.create(user)

            # Convert to response DTO
            return RegisterResponse(
                message="Registration successful",
                id=created_user.id,
                email=created_user.email,
                first_name=created_user.first_name,
                last_name=created_user.last_name,
                role=created_user.role.value,
                is_active=created_user.is_active,
                created_at=created_user.created_at.isoformat() if created_user.created_at else "",
                updated_at=created_user.updated_at.isoformat() if created_user.updated_at else ""
            )
        except Exception as e:
            raise ValidationException(f"Registration failed: {str(e)}")

    def login(self, request: LoginRequest) -> LoginResponse:
        """
        Authenticate a user.

        Args:
            request: LoginRequest DTO containing login credentials (already validated)

        Returns:
            LoginResponse DTO with user data

        Raises:
            ValidationException: If login fails
            UnauthorizedException: If credentials are invalid or account is deactivated
        """
        # Validation happens automatically in LoginRequest.__post_init__

        try:
            # Try to authenticate the user
            user = self.user_repository.authenticate(request.email, request.password)

            if not user:
                raise UnauthorizedException("Invalid email or password")

            # Check if user is active
            if not user.is_active:
                raise UnauthorizedException("Account is deactivated")

            # Convert to response DTO
            return LoginResponse(
                message="Login successful",
                id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role.value,
                is_active=user.is_active,
                created_at=user.created_at.isoformat() if user.created_at else "",
                updated_at=user.updated_at.isoformat() if user.updated_at else ""
            )
        except (UnauthorizedException, ValidationException):
            raise
        except Exception as e:
            raise ValidationException(f"Login failed: {str(e)}")

    def logout(self, request: LogoutRequest) -> LogoutResponse:
        """
        Logout a user.

        Args:
            request: LogoutRequest DTO containing user_id

        Returns:
            LogoutResponse DTO with success message

        Raises:
            NotFoundException: If user not found
        """
        user = self.user_repository.find_by_id(request.user_id)
        if not user:
            raise NotFoundException(f"User with id {request.user_id} not found")

        return LogoutResponse(message="Logout successful")