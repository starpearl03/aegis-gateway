import functools
from flask import current_app

from src.shared.data.database import db


def transactional(func):
    """
    Decorator that wraps a function in a database transactional.

    If the function completes successfully, the transactional is committed.
    If any exception occurs, the transactional is rolled back and the exception is re-raised.

    Usage:
        @transactional
        def create_product_with_images(self, product_data, images):
            # This entire method will run in a single transactional
            product = self.product_repository.create(product_data)
            for image in images:
                self.image_repository.create(image)
            return product

    Note:
        - Only use on service layer methods that need atomic operations
        - Don't nest @transactional decorators
        - The decorator handles commit/rollback automatically
        - Exceptions are re-raised after rollback for proper error handling
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Execute the function
            result = func(*args, **kwargs)

            # If we get here, function completed successfully
            db.session.commit()

            return result

        except Exception as e:
            # Function failed, rollback the transactional
            db.session.rollback()

            # Log the error for debugging
            current_app.logger.error(
                f"Transaction rolled back in {func.__name__}: {str(e)}"
            )

            # Re-raise the original exception
            raise

    return wrapper