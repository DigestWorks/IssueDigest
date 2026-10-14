"""Typed internal PostgreSQL evidence persistence, independent of app entrypoints."""

from .access import EvidenceAccessRepository
from .engine import create_storage_engine
from .identity import IdentityRepository
from .oauth import ConsumedLogin, OAuthRepository, PendingLogin
from .repository import EvidenceRepository, StorageConflict, StorageCorruption, StorageError
from .search import RebuildProjectionResult
from .sessions import AuthenticationDenied, IssuedSession, SessionRepository
from .workspace_access import WorkspaceAccessRepository

__all__ = [
    "RebuildProjectionResult",
    "ConsumedLogin",
    "OAuthRepository",
    "PendingLogin",
    "WorkspaceAccessRepository",
    "EvidenceRepository",
    "EvidenceAccessRepository",
    "IdentityRepository",
    "SessionRepository",
    "IssuedSession",
    "AuthenticationDenied",
    "StorageConflict",
    "StorageCorruption",
    "StorageError",
    "create_storage_engine",
]
