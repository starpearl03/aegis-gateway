from math import ceil

from src.modules.authentication.domain.models.user import User, UserRole
from src.modules.authentication.domain.repositories.user_repository import UserRepository
from src.modules.authentication.presentation.dtos.user_management import (
    CreateUserRequest, CreateUserResponse,
    UpdateUserRequest, UpdateUserResponse,
    DeleteUserRequest, DeleteUserResponse,
    ListUsersRequest, ListUsersResponse, UserData,
    GetUserRequest, GetUserResponse
)
from src.shared.configs.exceptions.exceptions import (
    AlreadyExistsException, ValidationException, NotFoundException
)


class UserManagementService:
    """
    Service for handling user management operations.
    Provides methods for CRUD operations on users.
    """

    def __init__(self):
        self.user_repository = UserRepository()

    def create_user(self, request: CreateUserRequest) -> CreateUserResponse:
        """
        Create a new user (admin functionality).

        Args:
            request: CreateUserRequest DTO containing user data

        Returns:
            CreateUserResponse DTO with created user data

        Raises:
            AlreadyExistsException: If email already exists
            ValidationException: If validation fails
        """
        # Check if email already exists
        if self.user_repository.email_exists(request.email):
            raise AlreadyExistsException(f"Email {request.email} already exists")

        # Parse role
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
                is_active=request.is_active
            )
            user.set_password(request.password)

            # Save to database
            created_user = self.user_repository.create(user)

            # Convert to response DTO
            return CreateUserResponse(
                message="User created successfully",
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
            raise ValidationException(f"User creation failed: {str(e)}")

    def update_user(self, request: UpdateUserRequest) -> UpdateUserResponse:
        """
        Update user details.

        Args:
            request: UpdateUserRequest DTO containing update data

        Returns:
            UpdateUserResponse DTO with updated user data

        Raises:
            NotFoundException: If user not found
            AlreadyExistsException: If new email already exists
            ValidationException: If validation fails
        """
        # Find user
        user = self.user_repository.find_by_id(request.user_id)
        if not user:
            raise NotFoundException(f"User with id {request.user_id} not found")

        try:
            # Update email if provided and different
            if request.email is not None and request.email != user.email:
                if self.user_repository.email_exists(request.email):
                    raise AlreadyExistsException(f"Email {request.email} already exists")
                user.email = request.email

            # Update first name if provided
            if request.first_name is not None:
                user.first_name = request.first_name

            # Update last name if provided
            if request.last_name is not None:
                user.last_name = request.last_name

            # Update role if provided
            if request.role is not None:
                try:
                    user.role = UserRole(request.role)
                except ValueError:
                    raise ValidationException(f"Invalid role: {request.role}")

            # Update is_active if provided
            if request.is_active is not None:
                user.is_active = request.is_active

            # Update password if provided
            if request.password is not None:
                user.set_password(request.password)

            # Save changes
            updated_user = self.user_repository.update(user)

            # Convert to response DTO
            return UpdateUserResponse(
                message="User updated successfully",
                id=updated_user.id,
                email=updated_user.email,
                first_name=updated_user.first_name,
                last_name=updated_user.last_name,
                role=updated_user.role.value,
                is_active=updated_user.is_active,
                created_at=updated_user.created_at.isoformat() if updated_user.created_at else "",
                updated_at=updated_user.updated_at.isoformat() if updated_user.updated_at else ""
            )
        except (NotFoundException, AlreadyExistsException, ValidationException):
            raise
        except Exception as e:
            raise ValidationException(f"User update failed: {str(e)}")

    def delete_user(self, request: DeleteUserRequest) -> DeleteUserResponse:
        """
        Soft delete a user.

        Args:
            request: DeleteUserRequest DTO containing user_id

        Returns:
            DeleteUserResponse DTO with success message

        Raises:
            NotFoundException: If user not found
        """
        user = self.user_repository.find_by_id(request.user_id)
        if not user:
            raise NotFoundException(f"User with id {request.user_id} not found")

        # Soft delete
        self.user_repository.delete(user)

        return DeleteUserResponse(
            message="User deleted successfully",
            user_id=request.user_id
        )

    def list_users(self, request: ListUsersRequest) -> ListUsersResponse:
        """
        List all users with pagination and optional filtering.

        Args:
            request: ListUsersRequest DTO containing pagination and filter params

        Returns:
            ListUsersResponse DTO with list of users and pagination info
        """
        try:
            # Build filter dict
            filter_dict = {}
            if request.role is not None:
                try:
                    filter_dict['role'] = UserRole(request.role)
                except ValueError:
                    raise ValidationException(f"Invalid role: {request.role}")
            if request.is_active is not None:
                filter_dict['is_active'] = request.is_active

            # Get paginated results
            if filter_dict:
                # Custom pagination with filters
                query = self.user_repository.model.query
                if not request.include_deleted:
                    query = query.filter_by(is_deleted=False)
                query = query.filter_by(**filter_dict)
                pagination = query.paginate(
                    page=request.page,
                    per_page=request.per_page,
                    error_out=False
                )
            else:
                # Use repository's paginate method
                pagination = self.user_repository.paginate(
                    page=request.page,
                    per_page=request.per_page,
                    include_deleted=request.include_deleted
                )

            # Convert users to DTOs
            user_data_list = []
            for user in pagination.items:
                user_data = UserData(
                    id=user.id,
                    email=user.email,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    role=user.role.value,
                    is_active=user.is_active,
                    created_at=user.created_at.isoformat() if user.created_at else "",
                    updated_at=user.updated_at.isoformat() if user.updated_at else ""
                )
                user_data_list.append(user_data)

            # Calculate total pages
            total_pages = ceil(pagination.total / request.per_page) if pagination.total > 0 else 0

            return ListUsersResponse(
                message="Users retrieved successfully",
                users=user_data_list,
                total=pagination.total,
                page=request.page,
                per_page=request.per_page,
                total_pages=total_pages
            )
        except ValidationException:
            raise
        except Exception as e:
            raise ValidationException(f"Failed to retrieve users: {str(e)}")

    def get_user(self, request: GetUserRequest) -> GetUserResponse:
        """
        Get a single user by ID.

        Args:
            request: GetUserRequest DTO containing user_id

        Returns:
            GetUserResponse DTO with user data

        Raises:
            NotFoundException: If user not found
        """
        user = self.user_repository.find_by_id(request.user_id)
        if not user:
            raise NotFoundException(f"User with id {request.user_id} not found")

        return GetUserResponse(
            message="User retrieved successfully",
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else "",
            updated_at=user.updated_at.isoformat() if user.updated_at else ""
        )