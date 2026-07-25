"""
Zerodha Kite Connect — Authentication Module

Handles the complete OAuth flow for Kite Connect API:
1. Login URL generation
2. Request Token handling
3. Session creation (API Key + Secret + Request Token → Access Token)
4. Token validation and storage
5. Re-login detection
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from kiteconnect import KiteConnect

from utils.logger import log_info, log_warn, log_error


class KiteAuthError(Exception):
    """Base exception for Kite authentication errors."""

    pass


class KiteAuthentication:
    """
    Manages Kite Connect authentication lifecycle.

    Reads credentials from environment variables and provides methods
    for the full OAuth flow and token management.
    """

    def __init__(self):
        self._api_key: str | None = None
        self._api_secret: str | None = None
        self._access_token: str | None = None
        self._kite: KiteConnect | None = None
        self._authenticated: bool = False
        self._last_auth_time: datetime | None = None
        self._user_id: str | None = None
        self._user_name: str | None = None
        self._user_email: str | None = None
        self._broker: str = "ZERODHA"
        self._exchange: str = "NSE"

        # Try to load from environment
        self._load_from_env()

    def _load_from_env(self):
        """Load credentials from environment variables."""
        self._api_key = os.getenv("KITE_API_KEY", "")
        self._api_secret = os.getenv("KITE_API_SECRET", "")
        self._access_token = os.getenv("KITE_ACCESS_TOKEN", "")

        if self._api_key:
            log_info("KiteAuth: loaded API key from environment")

        if self._access_token:
            log_info("KiteAuth: loaded access token from environment")
            # Try to validate the existing token
            self._try_init_with_token()

    def _try_init_with_token(self) -> bool:
        """Try to initialize KiteConnect with an existing access token."""
        if not self._api_key or not self._access_token:
            return False
        try:
            self._kite = KiteConnect(api_key=self._api_key)
            self._kite.set_access_token(self._access_token)
            # Test the token by fetching profile
            profile = self._kite.profile()
            self._user_id = profile.get("user_id", "")
            self._user_name = profile.get("user_name", "")
            self._user_email = profile.get("email", "")
            self._authenticated = True
            self._last_auth_time = datetime.now(timezone.utc)
            log_info(
                "KiteAuth: restored session",
                user_id=self._user_id,
                user_name=self._user_name,
            )
            return True
        except Exception as e:
            log_warn("KiteAuth: stored token invalid, re-authentication required", error=str(e))
            self._access_token = None
            self._kite = None
            return False

    @property
    def api_key(self) -> str:
        """Return the API key."""
        return self._api_key or ""

    @property
    def is_authenticated(self) -> bool:
        """Whether a valid authenticated session exists."""
        return self._authenticated

    @property
    def user_id(self) -> str:
        """Zerodha user ID."""
        return self._user_id or ""

    @property
    def kite(self) -> KiteConnect | None:
        """The authenticated KiteConnect instance."""
        return self._kite

    @property
    def exchange(self) -> str:
        return self._exchange

    # ── Login URL ──

    def get_login_url(self) -> str:
        """
        Generate the Kite Connect login URL.

        Returns:
            The login URL. User must visit this URL, login, and get the
            request_token from the redirect URL's query parameters.
        """
        if not self._api_key:
            raise KiteAuthError("KITE_API_KEY not configured")

        # Create a temporary KiteConnect instance for login URL generation
        kite = KiteConnect(api_key=self._api_key)
        url = kite.login_url()
        log_info("KiteAuth: generated login URL")
        return url

    # ── Session creation ──

    def create_session(self, request_token: str) -> dict[str, Any]:
        """
        Create a new session using the request token obtained from the login flow.

        Args:
            request_token: The request token from the login redirect

        Returns:
            Session information dict

        Raises:
            KiteAuthError: If session creation fails
        """
        if not self._api_key or not self._api_secret:
            raise KiteAuthError("KITE_API_KEY and KITE_API_SECRET must be configured")

        try:
            kite = KiteConnect(api_key=self._api_key)
            session_data = kite.generate_session(
                request_token=request_token,
                api_secret=self._api_secret,
            )

            self._access_token = session_data.get("access_token", "")
            self._kite = kite
            self._kite.set_access_token(self._access_token)

            # Extract profile info (Kite returns these at top level, not nested)
            session_user = session_data.get("user") or session_data
            if isinstance(session_user, dict):
                self._user_id = session_user.get("user_id", session_data.get("user_id", ""))
                self._user_name = session_user.get("user_name", session_data.get("user_name", ""))
                self._user_email = session_user.get("email", session_data.get("email", ""))
            else:
                self._user_id = session_data.get("user_id", "")
                self._user_name = session_data.get("user_name", "")
                self._user_email = session_data.get("email", "")
            self._authenticated = True
            self._last_auth_time = datetime.now(timezone.utc)

            log_info(
                "KiteAuth: session created",
                user_id=self._user_id,
                user_name=self._user_name,
            )

            return {
                "success": True,
                "access_token": self._access_token[:8] + "..." if self._access_token else "",
                "user_id": self._user_id,
                "user_name": self._user_name,
                "exchange": self._exchange,
                "broker": self._broker,
            }

        except Exception as e:
            self._authenticated = False
            self._kite = None
            log_error("KiteAuth: session creation failed", error=str(e))
            raise KiteAuthError(f"Session creation failed: {e}") from e

    # ── Token validation ──

    def validate_session(self) -> bool:
        """
        Validate the current session by fetching profile.

        Returns:
            True if session is valid, False otherwise.
        """
        if not self._kite or not self._access_token:
            self._authenticated = False
            return False

        try:
            self._kite.profile()
            self._authenticated = True
            self._last_auth_time = datetime.now(timezone.utc)
            return True
        except Exception:
            self._authenticated = False
            return False

    # ── Logout ──

    def logout(self):
        """Logout and clear the session."""
        try:
            if self._kite and self._access_token:
                self._kite.logout()
        except Exception:
            pass
        finally:
            self._kite = None
            self._access_token = None
            self._authenticated = False
            self._user_id = None
            self._user_name = None
            self._user_email = None
            log_info("KiteAuth: logged out")

    # ── Status ──

    def get_status(self) -> dict[str, Any]:
        """Return current authentication status."""
        return {
            "authenticated": self._authenticated,
            "user_id": self._user_id or "",
            "user_name": self._user_name or "",
            "broker": self._broker,
            "exchange": self._exchange,
            "last_auth_time": self._last_auth_time.isoformat() if self._last_auth_time else None,
            "has_api_key": bool(self._api_key),
            "has_api_secret": bool(self._api_secret),
            "has_access_token": bool(self._access_token),
        }
