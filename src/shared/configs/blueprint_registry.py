from typing import List
from flask import Blueprint


class BlueprintRegistry:
    """Registry to collect and manage Flask blueprints."""

    _blueprints: List[Blueprint] = []

    @classmethod
    def register(cls, blueprint: Blueprint) -> Blueprint:
        """
        Decorator to register a blueprint.

        Usage:
            @BlueprintRegistry.register
            auth_bp = Blueprint('auth', __name__)
        """
        if blueprint not in cls._blueprints:
            cls._blueprints.append(blueprint)
        return blueprint

    @classmethod
    def get_all(cls) -> List[Blueprint]:
        """Get all registered blueprints."""
        return cls._blueprints.copy()

    @classmethod
    def clear(cls):
        """Clear all registered blueprints (useful for testing)."""
        cls._blueprints.clear()


# Convenience decorator alias
register_blueprint = BlueprintRegistry.register