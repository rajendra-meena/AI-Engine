"""
Zerodha Kite Connect — Token Manager

Handles secure storage and retrieval of Kite access tokens.
Supports environment variables, file-based storage, and in-memory caching.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from utils.logger import log_info, log_warn, log_error

TOKEN_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "data_cache", "kite_token.json"
)


class TokenManager:
    """
    Manages Kite Connect access token lifecycle.

    Priority: Environment variable > File storage > Runtime set.
    """

    def __init__(self):
        self._access_token: str | None = None
        self._api_key: str | None = None
        self._api_secret: str | None = None
        self._user_id: str | None = None
        self._loaded_from: str | None = None
        self._created_at: datetime | None = None
        self._expires_at: datetime | None = None  # Kite tokens don't expire by default

        self._load_from_env()

    def _load_from_env(self):
        """Load credentials from environment."""
        self._api_key = os.getenv("KITE_API_KEY", "") or None
        self._api_secret = os.getenv("KITE_API_SECRET", "") or None
        token = os.getenv("KITE_ACCESS_TOKEN", "") or None

        if token:
            self._access_token = token
            self._loaded_from = "env"
            log_info("TokenManager: loaded access token from environment")

    # ── Storage ──

    def save_token(self, access_token: str, user_id: str = ""):
        """Persist access token to file."""
        self._access_token = access_token
        self._user_id = user_id
        self._created_at = datetime.now(timezone.utc)

        try:
            os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
            data = {
                "access_token": access_token,
                "user_id": user_id,
                "created_at": self._created_at.isoformat(),
            }
            with open(TOKEN_FILE, "w") as f:
                json.dump(data, f)
            log_info("TokenManager: token saved to file")
            self._loaded_from = "file"
        except Exception as e:
            log_warn("TokenManager: failed to save token", error=str(e))

    def load_token_from_file(self) -> str | None:
        """Load access token from persistent file storage."""
        try:
            if not os.path.exists(TOKEN_FILE):
                return None

            with open(TOKEN_FILE, "r") as f:
                data = json.load(f)

            token = data.get("access_token")
            if token:
                self._access_token = token
                self._user_id = data.get("user_id", "")
                created = data.get("created_at")
                if created:
                    self._created_at = datetime.fromisoformat(created)
                self._loaded_from = "file"
                log_info("TokenManager: token loaded from file")
                return token
        except Exception as e:
            log_warn("TokenManager: failed to load token from file", error=str(e))
        return None

    def clear_token(self):
        """Clear the stored access token."""
        self._access_token = None
        self._user_id = None
        self._created_at = None
        self._loaded_from = None

        try:
            if os.path.exists(TOKEN_FILE):
                os.remove(TOKEN_FILE)
                log_info("TokenManager: token file removed")
        except Exception as e:
            log_warn("TokenManager: failed to remove token file", error=str(e))

    # ── Access ──

    @property
    def access_token(self) -> str | None:
        return self._access_token

    @access_token.setter
    def access_token(self, value: str):
        self._access_token = value

    @property
    def api_key(self) -> str | None:
        return self._api_key

    @property
    def api_secret(self) -> str | None:
        return self._api_secret

    @property
    def is_authenticated(self) -> bool:
        return self._access_token is not None and len(self._access_token) > 0

    @property
    def user_id(self) -> str:
        return self._user_id or ""

    # ── Status ──

    def get_status(self) -> dict[str, Any]:
        return {
            "has_access_token": bool(self._access_token),
            "has_api_key": bool(self._api_key),
            "has_api_secret": bool(self._api_secret),
            "user_id": self._user_id or "",
            "loaded_from": self._loaded_from or "none",
            "created_at": self._created_at.isoformat() if self._created_at else None,
        }
