# src/shared/repositories.py
from typing import TypeVar, Generic, Type, List, Dict, Any, Optional

from src.shared.data.database import db

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """
    Generic base repositories providing common CRUD operations.
    Automatically handles soft deletes for all operations.

    This class serves as a base for all repositories classes and provides
    standard database operations with built-in soft delete support.

    Args:
        model: The SQLAlchemy model class this repositories manages

    Example:
        class UserRepository(BaseRepository[User]):
            def __init__(self):
                super().__init__(User)
    """

    def __init__(self, model: Type[T]) -> None:
        """
        Initialize the repositories with a specific model class.

        Args:
            model: The SQLAlchemy model class this repositories will manage

        Returns:
            None
        """
        self.model = model

    def find_all(self, include_deleted: bool = False) -> List[T]:
        """
        Retrieve all entities from the database.

        By default, excludes soft-deleted records. Set include_deleted=True
        to include soft-deleted records in the results.

        Args:
            include_deleted: Whether to include soft-deleted records (default: False)

        Returns:
            List of model instances matching the criteria

        Example:
            users = user_repo.find_all()  # Active users only
            all_users = user_repo.find_all(include_deleted=True)  # All users
        """
        query = self.model.query
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        return query.all()

    def find_by_id(self, id: str, include_deleted: bool = False) -> Optional[T]:
        """
        Find a single entity by its primary key ID.

        Returns None if the entity doesn't exist or is soft-deleted
        (unless include_deleted=True).

        Args:
            id: The primary key ID of the entity to find
            include_deleted: Whether to include soft-deleted records (default: False)

        Returns:
            The model instance if found, None otherwise

        Example:
            user = user_repo.find_by_id("uuid-string")
            deleted_user = user_repo.find_by_id("uuid-string", include_deleted=True)
        """
        entity = self.model.query.get(id)
        if entity and entity.is_deleted and not include_deleted:
            return None
        return entity

    def find_by_ids(self, ids: List[str], include_deleted: bool = False) -> List[T]:
        """
        Find multiple entities by their primary key IDs.

        Efficiently retrieves multiple records in a single query.
        Excludes soft-deleted records by default.

        Args:
            ids: List of primary key IDs to search for
            include_deleted: Whether to include soft-deleted records (default: False)

        Returns:
            List of model instances found (may be fewer than IDs provided)

        Example:
            users = user_repo.find_by_ids(["id1", "id2", "id3"])
        """
        query = self.model.query.filter(self.model.id.in_(ids))
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        return query.all()

    def find_one_by(self, filter_dict: Dict[str, Any], include_deleted: bool = False) -> Optional[T]:
        """
        Find a single entity matching the given filter criteria.

        Returns the first entity that matches all the provided criteria,
        or None if no match is found.

        Args:
            filter_dict: Dictionary of column names and values to filter by
            include_deleted: Whether to include soft-deleted records (default: False)

        Returns:
            The first model instance matching criteria, None if not found

        Example:
            user = user_repo.find_one_by({"email": "user@example.com"})
            admin = user_repo.find_one_by({"role": "admin", "is_active": True})
        """
        query = self.model.query
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        return query.filter_by(**filter_dict).first()

    def find_many_by(self, filter_dict: Dict[str, Any], include_deleted: bool = False) -> List[T]:
        """
        Find all entities matching the given filter criteria.

        Returns all entities that match the provided criteria.
        Use this when you expect multiple results.

        Args:
            filter_dict: Dictionary of column names and values to filter by
            include_deleted: Whether to include soft-deleted records (default: False)

        Returns:
            List of model instances matching the criteria (may be empty)

        Example:
            active_users = user_repo.find_many_by({"is_active": True})
            admins = user_repo.find_many_by({"role": "admin"})
        """
        query = self.model.query
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        return query.filter_by(**filter_dict).all()

    def create(self, entity: T) -> T:
        """
        Create a new entity in the database.

        Adds the entity to the database session, commits the transaction,
        and returns the saved entity with any auto-generated fields populated.
        Automatically rolls back on error.

        Args:
            entity: The model instance to save to the database

        Returns:
            The saved model instance with updated fields (e.g., ID, timestamps)

        Raises:
            Exception: If the database operation fails (after rollback)

        Example:
            user = User(name="John", email="john@example.com")
            saved_user = user_repo.create(user)
            print(saved_user.id)  # Auto-generated UUID
        """
        try:
            db.session.add(entity)
            db.session.commit()
            return entity
        except Exception:
            db.session.rollback()
            raise

    def create_many(self, entities: List[T]) -> List[T]:
        """
        Create multiple entities in the database efficiently.

        Performs a bulk insert operation for better performance when
        creating many records. All entities are saved in a single transaction.
        Automatically rolls back on error.

        Args:
            entities: List of model instances to save to the database

        Returns:
            List of saved model instances with updated fields

        Raises:
            Exception: If the database operation fails (after rollback)

        Example:
            users = [User(name=f"User {i}") for i in range(100)]
            saved_users = user_repo.create_many(users)
        """
        try:
            db.session.add_all(entities)
            db.session.commit()
            return entities
        except Exception:
            db.session.rollback()
            raise

    def update(self, entity: T) -> T:
        """
        Update an existing entity in the database.

        Commits any changes made to the entity instance to the database.
        The entity should already be attached to the session (e.g., retrieved
        via a find method). Automatically rolls back on error.

        Args:
            entity: The model instance with changes to save

        Returns:
            The updated model instance

        Raises:
            Exception: If the database operation fails (after rollback)

        Example:
            user = user_repo.find_by_id("some-id")
            user.name = "Updated Name"
            updated_user = user_repo.update(user)
        """
        try:
            db.session.commit()
            return entity
        except Exception:
            db.session.rollback()
            raise

    def update_many(self, entities: List[T]) -> List[T]:
        """
        Update multiple entities in the database in a single transaction.

        This method is more efficient than calling update() individually for each
        entity when you need to update multiple records. All changes are made to
        the entities in memory first, then committed together in one transaction.
        Automatically rolls back on error.

        Args:
            entities: List of model instances with changes to save

        Returns:
            List of updated model instances

        Raises:
            Exception: If the database operation fails (after rollback)

        Note:
            Make sure to modify the entity attributes before passing them to this method.
            The method only commits the changes; it does not modify the entities itself.

        Example:
            # Find multiple users and update their status
            inactive_users = user_repo.find_many_by({"last_login": old_date})
            for user in inactive_users:
                user.is_active = False
            updated_users = user_repo.update_many(inactive_users)

            # Bulk update token revocation
            tokens = token_repo.find_many_by({"user_id": user_id})
            for token in tokens:
                token.is_revoked = True
            token_repo.update_many(tokens)
        """
        try:
            # Entities are already attached to session from find operations
            # Just commit all pending changes in one transaction
            db.session.commit()
            return entities
        except Exception:
            db.session.rollback()
            raise

    def delete(self, entity: T) -> T:
        """
        Soft delete an entity (mark as deleted without removing from database).

        Sets the is_deleted flag to True instead of physically removing
        the record. This allows for data recovery and maintains referential
        integrity. Automatically rolls back on error.

        Args:
            entity: The model instance to soft delete

        Returns:
            The soft-deleted model instance

        Raises:
            Exception: If the database operation fails (after rollback)

        Example:
            user = user_repo.find_by_id("some-id")
            deleted_user = user_repo.delete(user)
            # Record still exists but is_deleted=True
        """
        try:
            entity.is_deleted = True
            db.session.commit()
            return entity
        except Exception:
            db.session.rollback()
            raise

    def delete_many(self, entities: List[T]) -> List[T]:
        """
        Soft delete multiple entities in a single transaction.

        Sets the is_deleted flag to True for all provided entities instead
        of physically removing them. This allows for bulk data recovery and
        maintains referential integrity. All deletions occur in one transaction
        for better performance. Automatically rolls back on error.

        Args:
            entities: List of model instances to soft delete

        Returns:
            List of soft-deleted model instances

        Raises:
            Exception: If the database operation fails (after rollback)

        Example:
            inactive_users = user_repo.find_many_by({"last_login": old_date})
            deleted_users = user_repo.delete_many(inactive_users)
            # All records still exist but is_deleted=True
        """
        try:
            for entity in entities:
                entity.is_deleted = True
            db.session.commit()
            return entities
        except Exception:
            db.session.rollback()
            raise

    def hard_delete(self, entity: T) -> None:
        """
        Permanently delete an entity from the database.

        Physically removes the record from the database. This operation
        cannot be undone. Use with caution as it may break referential
        integrity. Automatically rolls back on error.

        Args:
            entity: The model instance to permanently delete

        Returns:
            None

        Raises:
            Exception: If the database operation fails (after rollback)

        Warning:
            This permanently removes data and cannot be undone.
            Consider using soft delete instead.

        Example:
            user = user_repo.find_by_id("some-id")
            user_repo.hard_delete(user)  # Record permanently removed
        """
        try:
            db.session.delete(entity)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    def hard_delete_many(self, entities: List[T]) -> None:
        """
        Permanently delete multiple entities from the database in a single transaction.

        Physically removes all provided records from the database in one operation.
        This is more efficient than calling hard_delete individually. This operation
        cannot be undone. Use with caution as it may break referential integrity.
        Automatically rolls back on error.

        Args:
            entities: List of model instances to permanently delete

        Returns:
            None

        Raises:
            Exception: If the database operation fails (after rollback)

        Warning:
            This permanently removes data and cannot be undone.
            Consider using delete_many (soft delete) instead.

        Example:
            expired_tokens = token_repo.find_many_by({"is_expired": True})
            token_repo.hard_delete_many(expired_tokens)  # Records permanently removed
        """
        try:
            for entity in entities:
                db.session.delete(entity)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    def restore(self, entity: T) -> T:
        """
        Restore a soft-deleted entity.

        Sets the is_deleted flag back to False, making the entity
        visible in normal queries again. Only works on soft-deleted records.
        Automatically rolls back on error.

        Args:
            entity: The soft-deleted model instance to restore

        Returns:
            The restored model instance

        Raises:
            Exception: If the database operation fails (after rollback)

        Example:
            # Find a deleted user (must include deleted records)
            deleted_user = user_repo.find_by_id("some-id", include_deleted=True)
            restored_user = user_repo.restore(deleted_user)
        """
        try:
            entity.is_deleted = False
            db.session.commit()
            return entity
        except Exception:
            db.session.rollback()
            raise

    def exists(self, filter_dict: Dict[str, Any], include_deleted: bool = False) -> bool:
        """
        Check if any entity exists matching the given criteria.

        More efficient than find_one_by when you only need to know
        if a record exists without retrieving it.

        Args:
            filter_dict: Dictionary of column names and values to filter by
            include_deleted: Whether to include soft-deleted records (default: False)

        Returns:
            True if at least one matching entity exists, False otherwise

        Example:
            email_taken = user_repo.exists({"email": "user@example.com"})
            if not email_taken:
                # Safe to create user with this email
        """
        return self.count(filter_dict, include_deleted) > 0

    def count(self, filter_dict: Optional[Dict[str, Any]] = None, include_deleted: bool = False) -> int:
        """
        Count entities matching the given criteria.

        Returns the number of entities that match the filter criteria
        without loading the actual entities into memory.

        Args:
            filter_dict: Dictionary of column names and values to filter by (optional)
            include_deleted: Whether to include soft-deleted records (default: False)

        Returns:
            Number of entities matching the criteria

        Example:
            total_users = user_repo.count()
            active_users = user_repo.count({"is_active": True})
            all_users = user_repo.count(include_deleted=True)
        """
        query = self.model.query
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        if filter_dict:
            query = query.filter_by(**filter_dict)
        return query.count()

    def paginate(self, page: int = 1, per_page: int = 20, include_deleted: bool = False) -> Any:
        """
        Paginate query results for efficient large dataset handling.

        Returns a pagination object that contains the current page of results
        along with pagination metadata (total pages, current page, etc.).

        Args:
            page: Page number to retrieve (1-based, default: 1)
            per_page: Number of items per page (default: 20)
            include_deleted: Whether to include soft-deleted records (default: False)

        Returns:
            Flask-SQLAlchemy Pagination object with items and metadata

        Example:
            pagination = user_repo.paginate(page=2, per_page=10)
            users = pagination.items
            total_pages = pagination.pages
            has_next = pagination.has_next
        """
        query = self.model.query
        if not include_deleted:
            query = query.filter_by(is_deleted=False)
        return query.paginate(page=page, per_page=per_page, error_out=False)