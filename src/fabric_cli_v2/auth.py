# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Authentication for Fabric CLI v2 — built on ``azure-identity``.

Replaces the MSAL-based auth module from v1 with a streamlined
implementation using Azure Identity credentials.

Supported flows:
 - Interactive browser login (default for users)
 - Service principal (client secret or certificate)
 - Managed identity
 - Environment credentials (CI/CD)
 - Azure CLI credential (fallback)
 - Pre-set token via environment variable

Design goals:
 - Zero MSAL code — rely on azure-identity for all token management
 - Token caching handled by azure-identity internally
 - Compatible with ``azure.core.credentials.TokenCredential`` interface
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from azure.core.credentials import AccessToken, TokenCredential

# Scopes
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
STORAGE_SCOPE = "https://storage.azure.com/.default"
AZURE_SCOPE = "https://management.azure.com/.default"

# Environment variable keys
ENV_TOKEN = "FAB_TOKEN"
ENV_TOKEN_ONELAKE = "FAB_TOKEN_ONELAKE"
ENV_TOKEN_AZURE = "FAB_TOKEN_AZURE"
ENV_CLIENT_ID = "FAB_CLIENT_ID"
ENV_CLIENT_SECRET = "FAB_CLIENT_SECRET"
ENV_TENANT_ID = "FAB_TENANT_ID"
ENV_CERT_PATH = "FAB_CERT_PATH"
ENV_CERT_PASSWORD = "FAB_CERT_PASSWORD"
ENV_MANAGED_IDENTITY_CLIENT_ID = "FAB_MANAGED_IDENTITY_CLIENT_ID"

# Client ID for interactive login (public client)
DEFAULT_CLIENT_ID = "5814bfb4-2705-4994-b8d6-39aabeb5eaeb"
DEFAULT_AUTHORITY = "https://login.microsoftonline.com/common"


class FabricAuth:
    """Manages authentication state and credential creation.

    Usage::

        auth = FabricAuth()
        auth.login_interactive()          # or login_spn(), etc.
        token = auth.get_token(FABRIC_SCOPE)
        # token.token is the bearer string
    """

    def __init__(self) -> None:
        self._credential: Optional[TokenCredential] = None
        self._mode: Optional[str] = None  # "user" | "spn" | "managed_identity" | "env"
        self._tenant_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Login methods
    # ------------------------------------------------------------------

    def login_interactive(
        self,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
    ) -> None:
        """Interactive browser-based login."""
        from azure.identity import InteractiveBrowserCredential

        kwargs: dict[str, Any] = {}
        if tenant_id:
            kwargs["tenant_id"] = tenant_id
            self._tenant_id = tenant_id
        if client_id:
            kwargs["client_id"] = client_id
        else:
            kwargs["client_id"] = DEFAULT_CLIENT_ID

        self._credential = InteractiveBrowserCredential(**kwargs)
        self._mode = "user"

        # Force a token acquisition to validate the login
        self._credential.get_token(FABRIC_SCOPE)

    def login_spn(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: Optional[str] = None,
        cert_path: Optional[str] = None,
        cert_password: Optional[str] = None,
    ) -> None:
        """Service principal login (secret or certificate)."""
        self._tenant_id = tenant_id

        if cert_path:
            from azure.identity import CertificateCredential

            kwargs: dict[str, Any] = {
                "tenant_id": tenant_id,
                "client_id": client_id,
                "certificate_path": cert_path,
            }
            if cert_password:
                kwargs["password"] = cert_password
            self._credential = CertificateCredential(**kwargs)
        elif client_secret:
            from azure.identity import ClientSecretCredential

            self._credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
        else:
            raise ValueError("Either client_secret or cert_path is required for SPN login")

        self._mode = "spn"
        self._credential.get_token(FABRIC_SCOPE)

    def login_managed_identity(self, client_id: Optional[str] = None) -> None:
        """Managed identity login (system or user-assigned)."""
        from azure.identity import ManagedIdentityCredential

        kwargs: dict[str, Any] = {}
        if client_id:
            kwargs["client_id"] = client_id
        self._credential = ManagedIdentityCredential(**kwargs)
        self._mode = "managed_identity"

    def login_from_environment(self) -> None:
        """Login using environment variables or Azure CLI credential."""
        # Check for direct token first
        if os.environ.get(ENV_TOKEN):
            self._setup_env_token_credential()
            return

        # Check for SPN env vars
        tenant = os.environ.get(ENV_TENANT_ID)
        client = os.environ.get(ENV_CLIENT_ID)
        secret = os.environ.get(ENV_CLIENT_SECRET)
        cert = os.environ.get(ENV_CERT_PATH)
        mi_client = os.environ.get(ENV_MANAGED_IDENTITY_CLIENT_ID)

        if tenant and client and (secret or cert):
            self.login_spn(
                tenant_id=tenant,
                client_id=client,
                client_secret=secret,
                cert_path=cert,
                cert_password=os.environ.get(ENV_CERT_PASSWORD),
            )
            return

        if mi_client:
            self.login_managed_identity(client_id=mi_client)
            return

        # Fallback: try environment credential then Azure CLI
        from azure.identity import ChainedTokenCredential, AzureCliCredential, EnvironmentCredential

        self._credential = ChainedTokenCredential(
            EnvironmentCredential(),
            AzureCliCredential(),
        )
        self._mode = "env"

    def _setup_env_token_credential(self) -> None:
        """Create a static-token credential from FAB_TOKEN env var."""
        from azure.core.credentials import AccessToken

        class _StaticTokenCredential:
            """Credential that returns a pre-set token string."""

            def get_token(self, *scopes: str, **kwargs: Any) -> AccessToken:
                token = os.environ.get(ENV_TOKEN, "")
                return AccessToken(token=token, expires_on=int(time.time()) + 86400)

        self._credential = _StaticTokenCredential()  # type: ignore[assignment]
        self._mode = "env"

    # ------------------------------------------------------------------
    # Token access
    # ------------------------------------------------------------------

    def get_token(self, scope: str = FABRIC_SCOPE) -> AccessToken:
        """Get an access token for the given scope.

        Raises ``RuntimeError`` if not logged in.
        """
        if self._credential is None:
            raise RuntimeError(
                "Not authenticated. Run 'fab auth login' first."
            )
        from azure.core.credentials import AccessToken

        return self._credential.get_token(scope)

    def get_token_string(self, scope: str = FABRIC_SCOPE) -> str:
        """Convenience: return just the bearer token string."""
        return self.get_token(scope).token

    @property
    def credential(self) -> Optional[TokenCredential]:
        """The underlying azure-identity credential, or None."""
        return self._credential

    @property
    def is_authenticated(self) -> bool:
        return self._credential is not None

    @property
    def mode(self) -> Optional[str]:
        return self._mode

    @property
    def tenant_id(self) -> Optional[str]:
        return self._tenant_id

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    def logout(self) -> None:
        """Clear credential state."""
        self._credential = None
        self._mode = None
        self._tenant_id = None

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    _instance: Optional[FabricAuth] = None

    @classmethod
    def get_instance(cls) -> FabricAuth:
        """Return the global auth singleton."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
