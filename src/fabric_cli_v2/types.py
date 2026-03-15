# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Core type definitions for Fabric CLI v2.

Minimal enum and type system — defines only the element/item taxonomy
needed for path resolution, command validation, and API routing.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class ElementType(str, Enum):
    """Top-level element types in the Fabric hierarchy."""

    TENANT = "Tenant"
    WORKSPACE = "Workspace"
    PERSONAL = "Personal"
    FOLDER = "Folder"
    ITEM = "Item"
    ONELAKE = "OneLake"
    # Virtual (hidden) collections
    CAPACITY = "Capacity"
    CONNECTION = "Connection"
    GATEWAY = "Gateway"
    DOMAIN = "Domain"


class ItemType(str, Enum):
    """Fabric item types — each maps to a REST API resource path."""

    NOTEBOOK = "Notebook"
    REPORT = "Report"
    SEMANTIC_MODEL = "SemanticModel"
    LAKEHOUSE = "Lakehouse"
    WAREHOUSE = "Warehouse"
    DATA_PIPELINE = "DataPipeline"
    DATAFLOW = "Dataflow"
    ENVIRONMENT = "Environment"
    SPARK_JOB_DEFINITION = "SparkJobDefinition"
    KQL_DATABASE = "KQLDatabase"
    KQL_DASHBOARD = "KQLDashboard"
    KQL_QUERYSET = "KQLQueryset"
    EVENTHOUSE = "Eventhouse"
    EVENTSTREAM = "Eventstream"
    MIRRORED_DATABASE = "MirroredDatabase"
    SQL_DATABASE = "SQLDatabase"
    COPY_JOB = "CopyJob"
    REFLEX = "Reflex"
    DASHBOARD = "Dashboard"
    PAGINATED_REPORT = "PaginatedReport"
    SQL_ENDPOINT = "SQLEndpoint"
    MOUNTED_DATA_FACTORY = "MountedDataFactory"
    VARIABLE_LIBRARY = "VariableLibrary"
    GRAPH_QL_API = "GraphQLApi"
    COSMOS_DB_DATABASE = "CosmosDBDatabase"
    USER_DATA_FUNCTION = "UserDataFunction"
    GRAPH_QUERY_SET = "GraphQuerySet"

    @classmethod
    def from_string(cls, s: str) -> ItemType:
        """Case-insensitive lookup. Accepts both 'Notebook' and 'notebook'."""
        lookup = s.strip()
        for member in cls:
            if member.value.lower() == lookup.lower():
                return member
        # Also check enum names (NOTEBOOK, DATA_PIPELINE, etc.)
        upper = lookup.upper().replace(" ", "_")
        if upper in cls.__members__:
            return cls[upper]
        raise ValueError(f"Unknown item type: {s!r}")

    @property
    def api_path(self) -> str:
        """REST API collection name for this item type (e.g. 'notebooks')."""
        return _API_PATHS.get(self, self.value.lower() + "s")


# REST API resource path overrides (when pluralisation isn't trivial)
_API_PATHS: dict[ItemType, str] = {
    ItemType.NOTEBOOK: "notebooks",
    ItemType.REPORT: "reports",
    ItemType.SEMANTIC_MODEL: "semanticModels",
    ItemType.LAKEHOUSE: "lakehouses",
    ItemType.WAREHOUSE: "warehouses",
    ItemType.DATA_PIPELINE: "dataPipelines",
    ItemType.DATAFLOW: "dataflows",
    ItemType.ENVIRONMENT: "environments",
    ItemType.SPARK_JOB_DEFINITION: "sparkJobDefinitions",
    ItemType.KQL_DATABASE: "kqlDatabases",
    ItemType.KQL_DASHBOARD: "kqlDashboards",
    ItemType.KQL_QUERYSET: "kqlQuerysets",
    ItemType.EVENTHOUSE: "eventhouses",
    ItemType.EVENTSTREAM: "eventstreams",
    ItemType.MIRRORED_DATABASE: "mirroredDatabases",
    ItemType.SQL_DATABASE: "sqlDatabases",
    ItemType.COPY_JOB: "copyJobs",
    ItemType.REFLEX: "reflexes",
    ItemType.DASHBOARD: "dashboards",
    ItemType.PAGINATED_REPORT: "paginatedReports",
    ItemType.SQL_ENDPOINT: "sqlEndpoints",
    ItemType.MOUNTED_DATA_FACTORY: "mountedDataFactories",
    ItemType.VARIABLE_LIBRARY: "variableLibraries",
    ItemType.GRAPH_QL_API: "graphQLApis",
    ItemType.COSMOS_DB_DATABASE: "cosmosDBDatabases",
    ItemType.USER_DATA_FUNCTION: "userDataFunctions",
    ItemType.GRAPH_QUERY_SET: "graphQuerySets",
}


class OneLakeItemType(str, Enum):
    """OneLake sub-item types."""

    FILE = "file"
    FOLDER = "directory"
    TABLE = "table"
    SHORTCUT = "shortcut"


class OutputFormat(str, Enum):
    """Supported output formats."""

    TEXT = "text"
    JSON = "json"


# ---------------------------------------------------------------------------
# Hierarchy node (used by context/path resolution)
# ---------------------------------------------------------------------------


class FabricElement:
    """Lightweight representation of a node in the Fabric hierarchy."""

    __slots__ = ("name", "id", "element_type", "item_type", "parent", "extra")

    def __init__(
        self,
        name: str,
        element_type: ElementType,
        *,
        id: Optional[str] = None,
        item_type: Optional[ItemType] = None,
        parent: Optional[FabricElement] = None,
        extra: Optional[dict] = None,
    ) -> None:
        self.name = name
        self.id = id
        self.element_type = element_type
        self.item_type = item_type
        self.parent = parent
        self.extra = extra or {}

    # Convenience helpers

    @property
    def path(self) -> str:
        """Full path from root, e.g. ``/ws.Workspace/nb.Notebook``."""
        parts: list[str] = []
        node: Optional[FabricElement] = self
        while node is not None:
            parts.append(node.name)
            node = node.parent
        return "/" + "/".join(reversed(parts[:-1]))  # skip tenant

    def __repr__(self) -> str:
        return f"FabricElement({self.name!r}, {self.element_type.value})"
