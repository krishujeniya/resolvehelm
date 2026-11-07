"""Vercel Serverless Function entrypoint for ResolveHelm FastAPI backend."""

import sys
import urllib.parse
from pathlib import Path

# Add project root to sys.path so 'app' is discoverable
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from app.main import app as fastapi_app  # noqa: E402


async def app(scope, receive, send):
    """ASGI wrapper to handle Vercel path rewrites transparently."""
    if scope["type"] == "http":
        raw_query = scope.get("query_string", b"").decode("latin1")
        query_params = urllib.parse.parse_qs(raw_query)

        # Extract path forwarded by vercel.json rewrite rule
        if "__path__" in query_params:
            forwarded_path = query_params["__path__"][0]
            if not forwarded_path.startswith("/"):
                forwarded_path = "/" + forwarded_path
            scope["path"] = forwarded_path

            # Clean __path__ out of query string so route handlers receive pristine query params
            del query_params["__path__"]
            scope["query_string"] = urllib.parse.urlencode(
                query_params, doseq=True
            ).encode("latin1")

    await fastapi_app(scope, receive, send)


__all__ = ["app"]
