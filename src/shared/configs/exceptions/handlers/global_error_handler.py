from flask import request, render_template

from src.shared.configs.exceptions.exceptions import AppException


def register_global_error_handlers(app):
    """Register error handlers for server-side template rendering"""

    @app.errorhandler(AppException)
    def handle_app_exception(error):
        """Handle all custom application exceptions"""
        return render_template(
            'errors/error.jinja2',
            error_message=error.message,
            status_code=error.status_code
        ), error.status_code

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 Not Found"""
        return render_template('errors/404.jinja2'), 404

    @app.errorhandler(403)
    def handle_forbidden(error):
        """Handle 403 Forbidden"""
        return render_template('errors/403.jinja2'), 403

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle 405 Method Not Allowed"""
        return render_template('errors/405.jinja2'), 405

    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 Internal Server Error"""
        app.logger.error(f"Internal server error: {error}", exc_info=True)
        return render_template('errors/500.jinja2'), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Catch-all handler for unexpected errors"""
        app.logger.error(f"Unexpected error: {error}", exc_info=True)
        return render_template(
            'errors/500.jinja2',
            error_message="An unexpected error occurred"
        ), 500