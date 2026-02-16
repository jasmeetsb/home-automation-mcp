#!/usr/bin/env python3
"""OAuth flow to obtain Google Nest access and refresh tokens.

Usage:
    cd home-automation-mcp
    PYTHONPATH=$PWD uv run python sandbox/nest_oauth.py
"""

import asyncio
import secrets
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from dotenv import dotenv_values, set_key


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""

    auth_code: str | None = None
    auth_error: str | None = None

    def do_GET(self):
        query = urlparse(self.path).query
        params = parse_qs(query)

        if "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Authorization Successful!</h1>"
                b"<p>You can close this window.</p></body></html>"
            )
        elif "error" in params:
            OAuthCallbackHandler.auth_error = params["error"][0]
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                f"<html><body><h1>Authorization Failed</h1>"
                f"<p>Error: {params['error'][0]}</p></body></html>".encode()
            )
        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Invalid callback</h1></body></html>")

    def log_message(self, format, *args):
        pass


ENV_PATH = Path(__file__).parent.parent / ".env"
TOKEN_URL = "https://www.googleapis.com/oauth2/v4/token"
OAUTH_URL = "https://nestservices.google.com/partnerconnections/{project_id}/auth"
SCOPES = ["https://www.googleapis.com/auth/sdm.service"]


def load_config() -> dict:
    """Load and validate config from .env."""
    if not ENV_PATH.exists():
        print(f"Error: .env file not found at {ENV_PATH}", file=sys.stderr)
        sys.exit(1)

    config = dotenv_values(ENV_PATH)
    required = ["GOOGLE_PROJECT_ID", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI"]
    missing = [k for k in required if not config.get(k)]

    if missing:
        print(f"Error: Missing in .env: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    return config


async def exchange_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict:
    """Exchange authorization code for tokens."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
        )
        response.raise_for_status()
        return response.json()


async def main():
    print("=" * 60)
    print("Google Nest OAuth 2.0 Authorization")
    print("=" * 60)
    print()

    config = load_config()
    project_id = config["GOOGLE_PROJECT_ID"]
    client_id = config["GOOGLE_CLIENT_ID"]
    client_secret = config["GOOGLE_CLIENT_SECRET"]
    redirect_uri = config["GOOGLE_REDIRECT_URI"]

    # Build authorization URL
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "access_type": "offline",
        "prompt": "consent",
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": secrets.token_urlsafe(32),
    }
    auth_url = f"{OAUTH_URL.format(project_id=project_id)}?{urlencode(params)}"

    print("Opening browser for authorization...")
    print()
    print("If the browser doesn't open, copy this URL:")
    print(auth_url)
    print()
    webbrowser.open(auth_url)

    # Wait for callback
    port = int(urlparse(redirect_uri).port or 8090)
    print(f"Waiting for callback on http://localhost:{port} ...")
    server = HTTPServer(("localhost", port), OAuthCallbackHandler)
    server_thread = Thread(target=server.handle_request, daemon=True)
    server_thread.start()
    server_thread.join(timeout=120)
    server.server_close()

    if OAuthCallbackHandler.auth_error:
        print(f"Authorization failed: {OAuthCallbackHandler.auth_error}", file=sys.stderr)
        sys.exit(1)

    if not OAuthCallbackHandler.auth_code:
        print("Authorization timed out.", file=sys.stderr)
        sys.exit(1)

    print("Authorization code received!")
    print()

    # Exchange for tokens
    try:
        tokens = await exchange_code(
            client_id, client_secret, OAuthCallbackHandler.auth_code, redirect_uri
        )
    except httpx.HTTPError as e:
        print(f"Error exchanging code for tokens: {e}", file=sys.stderr)
        sys.exit(1)

    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    if not access_token:
        print("Error: No access token received", file=sys.stderr)
        sys.exit(1)

    # Save to .env
    set_key(str(ENV_PATH), "GOOGLE_ACCESS_TOKEN", access_token)
    if refresh_token:
        set_key(str(ENV_PATH), "GOOGLE_REFRESH_TOKEN", refresh_token)
    else:
        print("WARNING: No refresh token received. You may need to revoke and retry.")

    print("=" * 60)
    print("SUCCESS - Tokens saved to .env")
    print("=" * 60)
    print(f"Access Token:  {access_token[:50]}...")
    print(f"Refresh Token: {(refresh_token[:50] + '...') if refresh_token else 'None'}")
    print(f"Expires In:    {tokens.get('expires_in', '?')} seconds")
    print()


if __name__ == "__main__":
    asyncio.run(main())
