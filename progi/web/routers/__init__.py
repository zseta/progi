from __future__ import annotations

from fastapi import Request


def is_partial_request(request: Request) -> bool:
    """Return True when the request comes from Alpine AJAX (x-target link/form).

    Alpine AJAX sends ``X-Alpine-Request: true`` on every fetch it initiates,
    so we can use it to decide between returning a full page or just a content
    partial.
    """
    return request.headers.get("X-Alpine-Request") == "true"


def base_template(request: Request) -> str:
    """Return the appropriate base template name for the request.

    Full page loads extend ``base.html`` (shell + nav); Alpine AJAX requests
    extend ``base_partial.html`` (content block only).
    """
    return "base_partial.html" if is_partial_request(request) else "base.html"
