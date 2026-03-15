# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Minimal HTTP client for Fabric CLI v2.

A thin wrapper around ``requests`` that adds:
 - Bearer token injection from :class:`FabricAuth`
 - Automatic retry with exponential back-off (429, 502-504)
 - Continuation-token pagination
 - Long-running operation (LRO) polling
 - Audience-aware endpoint routing

All API calls in the CLI should go through :func:`request`.
"""

from __future__ import annotations

import time
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter, Retry

from fabric_cli_v2 import __version__

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_FABRIC = "api.fabric.microsoft.com"
API_ONELAKE = "onelake.dfs.fabric.microsoft.com"
API_AZURE = "management.azure.com"

API_VERSION = "v1"

_SCOPE_MAP = {
    API_FABRIC: "https://api.fabric.microsoft.com/.default",
    API_ONELAKE: "https://storage.azure.com/.default",
    API_AZURE: "https://management.azure.com/.default",
}

_USER_AGENT = f"fabric-cli/{__version__}"


# ---------------------------------------------------------------------------
# Session factory (with retry)
# ---------------------------------------------------------------------------

_session: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        )
        _session.mount("https://", HTTPAdapter(max_retries=retries))
    return _session


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


_MAX_RETRIES = 5


def request(
    method: str,
    path: str,
    *,
    host: str = API_FABRIC,
    json: Any = None,
    data: Any = None,
    params: Optional[dict[str, str]] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: int = 240,
    paginate: bool = False,
    wait_lro: bool = True,
    _retry_count: int = 0,
) -> dict[str, Any]:
    """Execute an authenticated HTTP request to a Fabric API.

    Parameters
    ----------
    method : str
        HTTP verb (GET, POST, PUT, PATCH, DELETE).
    path : str
        Relative path after ``/v1/`` (e.g. ``workspaces``).
    host : str
        API host (default: Fabric core API).
    json : Any
        JSON body payload.
    data : Any
        Raw body payload.
    params : dict
        Query-string parameters.
    headers : dict
        Extra headers (merged with defaults).
    timeout : int
        Request timeout in seconds.
    paginate : bool
        If True, follow ``continuationToken`` to collect all pages.
    wait_lro : bool
        If True, poll long-running operations until complete.

    Returns
    -------
    dict
        Parsed JSON response (or ``{"status_code": N}`` for empty bodies).
    """
    from fabric_cli_v2.auth import FabricAuth

    auth = FabricAuth.get_instance()
    scope = _SCOPE_MAP.get(host, "https://api.fabric.microsoft.com/.default")
    token = auth.get_token_string(scope)

    url = f"https://{host}/{API_VERSION}/{path.lstrip('/')}"
    req_headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": _USER_AGENT,
        "Content-Type": "application/json",
    }
    if headers:
        req_headers.update(headers)

    session = _get_session()

    resp = session.request(
        method,
        url,
        json=json,
        data=data,
        params=params,
        headers=req_headers,
        timeout=timeout,
    )

    # -- Rate limiting
    if resp.status_code == 429:
        if _retry_count >= _MAX_RETRIES:
            _raise_for_status(resp)
        retry_after = int(resp.headers.get("Retry-After", "5"))
        time.sleep(retry_after)
        return request(method, path, host=host, json=json, data=data,
                       params=params, headers=headers, timeout=timeout,
                       paginate=paginate, wait_lro=wait_lro,
                       _retry_count=_retry_count + 1)

    # -- Error handling
    if resp.status_code >= 400:
        _raise_for_status(resp)

    # -- LRO polling (202 Accepted)
    if resp.status_code == 202 and wait_lro:
        return _poll_lro(resp, session, req_headers, timeout)

    # -- Empty body
    if resp.status_code == 204 or not resp.text:
        return {"status_code": resp.status_code}

    result = resp.json()

    # -- Pagination
    if paginate and "continuationToken" in result:
        all_values = list(result.get("value", []))
        token_key = result["continuationToken"]
        while token_key:
            p = dict(params or {})
            p["continuationToken"] = token_key
            next_resp = session.request(
                method, url, params=p, headers=req_headers, timeout=timeout
            )
            next_resp.raise_for_status()
            page = next_resp.json()
            all_values.extend(page.get("value", []))
            token_key = page.get("continuationToken")
        result["value"] = all_values
        result.pop("continuationToken", None)

    return result


# ---------------------------------------------------------------------------
# LRO polling
# ---------------------------------------------------------------------------


MAX_LRO_POLL_ITERATIONS = 120  # ~10 min at default 5s retry intervals


def _poll_lro(
    resp: requests.Response,
    session: requests.Session,
    headers: dict[str, str],
    timeout: int,
) -> dict[str, Any]:
    """Poll a long-running operation until completion."""
    location = resp.headers.get("Location") or resp.headers.get("Operation-Location")
    if not location:
        return resp.json() if resp.text else {"status_code": resp.status_code}

    retry_after = int(resp.headers.get("Retry-After", "5"))

    for _ in range(MAX_LRO_POLL_ITERATIONS):
        time.sleep(retry_after)
        poll = session.get(location, headers=headers, timeout=timeout)
        if poll.status_code >= 400:
            _raise_for_status(poll)

        if poll.status_code == 200:
            body = poll.json() if poll.text else {}
            status = body.get("status", "").lower()
            if status in ("succeeded", "completed", ""):
                # Try to fetch the result from the Location header
                result_url = body.get("resourceLocation")
                if result_url:
                    final = session.get(result_url, headers=headers, timeout=timeout)
                    if final.status_code < 400 and final.text:
                        return final.json()
                return body
            if status in ("failed", "cancelled"):
                raise RuntimeError(f"Operation {status}: {body}")
            retry_after = int(poll.headers.get("Retry-After", str(retry_after)))

    raise TimeoutError("Long-running operation timed out")


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def _raise_for_status(resp: requests.Response) -> None:
    """Raise a descriptive error from an HTTP error response."""
    try:
        body = resp.json()
    except Exception:
        body = {"message": resp.text or f"HTTP {resp.status_code}"}

    # Fabric API error shape
    error = body.get("error", body)
    code = error.get("errorCode") or error.get("code") or str(resp.status_code)
    message = error.get("message") or str(body)
    request_id = error.get("requestId") or resp.headers.get("x-ms-request-id", "")

    detail = f"[{code}] {message}"
    if request_id:
        detail += f"\n  Request Id: {request_id}"

    raise RuntimeError(detail)
