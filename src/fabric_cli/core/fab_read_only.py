# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import re
from argparse import Namespace

from fabric_cli.core import fab_constant, fab_state_config
from fabric_cli.core.fab_exceptions import FabricCLIError
from fabric_cli.errors import ErrorMessages
from fabric_cli.utils.fab_util import GUID_PATTERN_STR

# These Fabric POST endpoints read remote state without modifying it.
_READ_POST_PATHS = (
    r"catalog/search",
    rf"workspaces/{GUID_PATTERN_STR}/items/{GUID_PATTERN_STR}/getDefinition",
    rf"workspaces/{GUID_PATTERN_STR}/items/bulkExportDefinitions",
)
_METHOD_OVERRIDE_HEADERS = {
    "x-http-method",
    "x-http-method-override",
    "x-method-override",
}


def is_enabled() -> bool:
    """Return whether remote mutations are disabled in the current configuration."""
    return (
        str(fab_state_config.get_config(fab_constant.FAB_READ_ONLY_MODE)).lower()
        == "true"
    )


def ensure_writes_allowed(operation: str) -> None:
    """Reject a remote mutation before invoking an external client."""
    if is_enabled():
        _raise_read_only_error(operation)


def check_request(args: Namespace) -> None:
    """Allow only read methods and explicitly supported read-only Fabric POSTs."""
    method = getattr(args, "method", "get").lower()
    headers = getattr(args, "headers", None)
    if isinstance(headers, dict) and any(
        key.lower() in _METHOD_OVERRIDE_HEADERS for key in headers
    ):
        _raise_read_only_error("HTTP method override")

    if method in ("get", "head"):
        return
    if method == "post" and getattr(args, "audience", None) in (None, "fabric"):
        path = args.uri.split("?", 1)[0].lstrip("/")
        if any(
            re.fullmatch(pattern, path, re.IGNORECASE) for pattern in _READ_POST_PATHS
        ):
            return
    _raise_read_only_error(f"{method.upper()} request")


def _raise_read_only_error(operation: str) -> None:
    raise FabricCLIError(
        ErrorMessages.Common.read_only_operation(operation),
        fab_constant.ERROR_READ_ONLY_MODE,
    )
