from typing import Protocol, runtime_checkable
from enum import Enum


@runtime_checkable
class AuthUserProtocol(Protocol):
    """
    Protocol defining the required attributes for any model
    that can be used with SessionManager.

    Any model used with SessionManager must have these attributes.
    """
    id: str
    email: str
    first_name: str
    last_name: str

    @property
    def role(self) -> Enum:
        """Role must be an Enum with a .value attribute"""
        ...