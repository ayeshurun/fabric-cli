# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Authentication commands: login, logout, status."""

from __future__ import annotations

from typing import Optional

import typer
from typing import Annotated

auth_app = typer.Typer(
    name="auth",
    help="Manage authentication for Fabric CLI.",
    no_args_is_help=True,
)


@auth_app.command("login")
def login_command(
    tenant_id: Annotated[
        Optional[str],
        typer.Option("--tenant", "-t", help="Azure AD tenant ID."),
    ] = None,
    client_id: Annotated[
        Optional[str],
        typer.Option("--client-id", help="Service principal client ID."),
    ] = None,
    client_secret: Annotated[
        Optional[str],
        typer.Option("--client-secret", help="Service principal secret."),
    ] = None,
    cert_path: Annotated[
        Optional[str],
        typer.Option("--certificate", help="Path to certificate file."),
    ] = None,
    managed_identity: Annotated[
        bool,
        typer.Option("--managed-identity", help="Use managed identity."),
    ] = False,
    use_environment: Annotated[
        bool,
        typer.Option("--environment", help="Use environment variables."),
    ] = False,
) -> None:
    """Authenticate to Microsoft Fabric."""
    from fabric_cli_v2.auth import FabricAuth
    from fabric_cli_v2 import output

    auth = FabricAuth.get_instance()

    try:
        if use_environment:
            auth.login_from_environment()
            output.print_success(f"Logged in via environment credentials")
        elif managed_identity:
            auth.login_managed_identity(client_id=client_id)
            output.print_success("Logged in via managed identity")
        elif client_id and (client_secret or cert_path):
            if not tenant_id:
                output.print_error("--tenant is required for service principal login")
                raise typer.Exit(code=1)
            auth.login_spn(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
                cert_path=cert_path,
            )
            output.print_success(f"Logged in as service principal {client_id}")
        else:
            auth.login_interactive(tenant_id=tenant_id, client_id=client_id)
            output.print_success("Logged in interactively")
    except Exception as exc:
        output.print_error(f"Login failed: {exc}")
        raise typer.Exit(code=1)


@auth_app.command("logout")
def logout_command() -> None:
    """Clear authentication state."""
    from fabric_cli_v2.auth import FabricAuth
    from fabric_cli_v2 import output

    FabricAuth.get_instance().logout()
    output.print_success("Logged out")


@auth_app.command("status")
def status_command(
    output_format: Annotated[
        Optional[str],
        typer.Option("--output", "-o", help="Output format."),
    ] = None,
) -> None:
    """Show current authentication status."""
    from fabric_cli_v2.auth import FabricAuth
    from fabric_cli_v2 import output

    auth = FabricAuth.get_instance()
    fmt = output_format or "text"

    info = {
        "authenticated": auth.is_authenticated,
        "mode": auth.mode,
        "tenant_id": auth.tenant_id,
    }

    if fmt == "json":
        output.print_json(info)
    else:
        if auth.is_authenticated:
            output.print_success(f"Authenticated ({auth.mode})")
            if auth.tenant_id:
                output.print_info(f"  Tenant: {auth.tenant_id}")
        else:
            output.print_warning("Not authenticated. Run 'fab auth login'.")
