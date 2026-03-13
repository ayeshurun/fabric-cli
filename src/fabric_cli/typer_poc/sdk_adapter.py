# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
SDK Adapter PoC — Demonstrates how ``microsoft-fabric-api`` can replace
raw ``requests``-based API calls in the CLI.

This module provides an adapter layer that:
1. Wraps the SDK's ``FabricClient`` with the CLI's authentication context
2. Falls back to the existing raw HTTP client when the SDK doesn't cover an API
3. Returns data in the format expected by the CLI's output layer

This is a *proof of concept* and is not wired into production code.

Usage example (conceptual)::

    from fabric_cli.typer_poc.sdk_adapter import FabricSDKAdapter

    adapter = FabricSDKAdapter(credential)
    workspaces = adapter.list_workspaces()
    items = adapter.list_items(workspace_id="...")
"""

from __future__ import annotations

from typing import Any, Optional


class FabricSDKAdapter:
    """Adapter bridging ``microsoft-fabric-api`` SDK to the CLI's data layer.

    The adapter attempts to use the official SDK for supported operations
    and falls back to the existing ``fab_api_client.do_request()`` for
    operations not yet covered.

    Parameters
    ----------
    credential : object
        An ``azure-identity`` credential (e.g., ``DefaultAzureCredential``,
        ``InteractiveBrowserCredential``).  During the PoC, passing ``None``
        is allowed and the adapter will only use the fallback path.
    """

    def __init__(self, credential: Any = None) -> None:
        self._credential = credential
        self._sdk_client: Any = None
        self._sdk_available = False

        # Try to import the SDK — it's optional during the PoC phase
        try:
            from microsoft_fabric_api import FabricClient

            if credential is not None:
                self._sdk_client = FabricClient(credential)
                self._sdk_available = True
        except ImportError:
            pass

    @property
    def sdk_available(self) -> bool:
        """Return True if the ``microsoft-fabric-api`` SDK is initialized."""
        return self._sdk_available

    # ------------------------------------------------------------------
    # Workspace operations
    # ------------------------------------------------------------------

    def list_workspaces(self) -> list[dict[str, Any]]:
        """List all workspaces accessible to the authenticated user.

        SDK path:
            ``client.core.workspaces.list_workspaces()``

        Fallback:
            ``GET /v1/workspaces`` via ``fab_api_client.do_request()``
        """
        if self._sdk_available:
            workspaces = list(self._sdk_client.core.workspaces.list_workspaces())
            return [
                {
                    "id": ws.id,
                    "displayName": ws.display_name,
                    "capacityId": getattr(ws, "capacity_id", None),
                    "type": "Workspace",
                }
                for ws in workspaces
            ]

        # Fallback to existing client
        return self._fallback_get("workspaces")

    def get_workspace(self, workspace_id: str) -> dict[str, Any]:
        """Get a single workspace by ID.

        SDK path:
            ``client.core.workspaces.get_workspace(workspace_id)``
        """
        if self._sdk_available:
            ws = self._sdk_client.core.workspaces.get_workspace(workspace_id)
            return {
                "id": ws.id,
                "displayName": ws.display_name,
                "capacityId": getattr(ws, "capacity_id", None),
                "type": "Workspace",
            }

        return self._fallback_get(f"workspaces/{workspace_id}")

    # ------------------------------------------------------------------
    # Item operations
    # ------------------------------------------------------------------

    def list_items(self, workspace_id: str) -> list[dict[str, Any]]:
        """List all items in a workspace.

        SDK path:
            ``client.core.items.list_items(workspace_id)``

        Fallback:
            ``GET /v1/workspaces/{id}/items``
        """
        if self._sdk_available:
            items = list(self._sdk_client.core.items.list_items(workspace_id))
            return [
                {
                    "id": item.id,
                    "displayName": item.display_name,
                    "type": getattr(item, "type", None),
                }
                for item in items
            ]

        return self._fallback_get(f"workspaces/{workspace_id}/items")

    def get_item(self, workspace_id: str, item_id: str) -> dict[str, Any]:
        """Get a single item by workspace and item IDs.

        SDK path:
            ``client.core.items.get_item(workspace_id, item_id)``
        """
        if self._sdk_available:
            item = self._sdk_client.core.items.get_item(workspace_id, item_id)
            return {
                "id": item.id,
                "displayName": item.display_name,
                "type": getattr(item, "type", None),
            }

        return self._fallback_get(f"workspaces/{workspace_id}/items/{item_id}")

    # ------------------------------------------------------------------
    # Capacity operations (example of SDK-not-yet-covered fallback)
    # ------------------------------------------------------------------

    def list_capacities(self) -> list[dict[str, Any]]:
        """List capacities — demonstrates fallback for APIs not in SDK."""
        # The SDK may not cover capacity listing yet
        if self._sdk_available and hasattr(self._sdk_client, "admin"):
            try:
                caps = list(self._sdk_client.admin.capacities.list_capacities())
                return [
                    {
                        "id": cap.id,
                        "displayName": cap.display_name,
                        "sku": getattr(cap, "sku", None),
                    }
                    for cap in caps
                ]
            except (AttributeError, NotImplementedError):
                pass

        return self._fallback_get("capacities")

    # ------------------------------------------------------------------
    # Fallback — delegates to existing raw HTTP client
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback_get(uri: str) -> list[dict[str, Any]] | dict[str, Any]:
        """Fallback path using the existing ``fab_api_client.do_request()``.

        In the actual integration, this would call::

            from fabric_cli.client import fab_api_client
            args = Namespace(method="get", uri=uri, ...)
            response = fab_api_client.do_request(args)
            return response.json()

        For the PoC, we return a placeholder.
        """
        return {"_fallback": True, "uri": uri, "value": []}
