"""Environment Safety — strict CONTROLLED_LIVE environment protection.

Phase 55: The application must NOT accidentally enter live mode because of
missing/malformed environment variables, dev/test/staging context, or defaults.
If live configuration is ambiguous: BLOCK. Never silently fall back to real credentials.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Required environment for real broker execution ──

REQUIRED_LIVE_ENV_VARS = [
    "KITE_API_KEY",
    "KITE_API_SECRET",
    "KITE_ACCESS_TOKEN",
]

ALLOWED_PRODUCTION_ENVIRONMENTS = {"production", "prod", "live"}

FORBIDDEN_ENVIRONMENTS = {"development", "dev", "test", "staging", "local", ""}

SENSITIVE_ENV_VARS = [
    "KITE_API_KEY",
    "KITE_API_SECRET",
    "KITE_ACCESS_TOKEN",
    "ZERODHA_API_KEY",
    "ZERODHA_API_SECRET",
    "ZERODHA_ACCESS_TOKEN",
]


def _sanitize_env(env_name: str) -> str:
    """Return masked representation of a sensitive env var name."""
    return f"{env_name}=***"


@dataclass
class EnvironmentSafetyResult:
    """Result of environment safety validation."""
    safe: bool = False
    environment: str = ""
    controlled_live_enabled: bool = False
    missing_vars: list[str] = field(default_factory=list)
    forbidden_environment: bool = False
    ambiguous_configuration: bool = False
    errors: list[str] = field(default_factory=list)
    checked_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "safe": self.safe,
            "environment": self.environment,
            "controlled_live_enabled": self.controlled_live_enabled,
            "missing_vars": self.missing_vars,
            "forbidden_environment": self.forbidden_environment,
            "ambiguous_configuration": self.ambiguous_configuration,
            "errors": self.errors,
            "checked_at": self.checked_at,
        }


class EnvironmentSafety:
    """Validates that the environment is safe for CONTROLLED_LIVE execution.

    Rules:
    1. APP_ENV must be explicitly set to 'production' or 'prod'
    2. Development, test, staging, local environments are BLOCKED
    3. All required Kite env vars must be present
    4. No ambiguous or default configuration
    5. CONTROLLED_LIVE must be explicitly enabled via env or config
    """

    def __init__(self):
        self._audit_log = None

    def set_audit_log(self, audit_log: Any) -> None:
        self._audit_log = audit_log

    def check(self) -> EnvironmentSafetyResult:
        """Run all environment safety checks.

        Returns:
            EnvironmentSafetyResult with safe=False if ANY check fails.
        """
        result = EnvironmentSafetyResult()
        errors: list[str] = []

        # 1. Check APP_ENV
        app_env = os.environ.get("APP_ENV", "").lower().strip()
        result.environment = app_env or "not_set"

        if not app_env:
            errors.append("APP_ENV not set — cannot determine environment")
            result.ambiguous_configuration = True
        elif app_env in FORBIDDEN_ENVIRONMENTS:
            errors.append(f"Forbidden environment: '{app_env}'")
            result.forbidden_environment = True
        elif app_env not in ALLOWED_PRODUCTION_ENVIRONMENTS:
            errors.append(f"Unknown environment: '{app_env}' — must be one of {ALLOWED_PRODUCTION_ENVIRONMENTS}")
            result.ambiguous_configuration = True

        # 2. Check CONTROLLED_LIVE explicitly enabled
        controlled_live_env = os.environ.get("CONTROLLED_LIVE_ENABLED", "").lower().strip()
        result.controlled_live_enabled = controlled_live_env in ("1", "true", "yes")

        if not result.controlled_live_enabled:
            errors.append(
                "CONTROLLED_LIVE_ENABLED not set to 'true' — "
                "set CONTROLLED_LIVE_ENABLED=true in environment"
            )

        # 3. Check required Kite env vars
        missing: list[str] = []
        for var in REQUIRED_LIVE_ENV_VARS:
            if not os.environ.get(var, "").strip():
                missing.append(var)

        if missing:
            result.missing_vars = missing
            errors.append(f"Missing required environment variables: {', '.join(missing)}")

        # 4. Check for security-sensitive vars leaked to unexpected places
        # (This is a runtime check — the presence of credentials in non-production
        # environments is a security concern)
        if result.forbidden_environment or result.ambiguous_configuration:
            for var in SENSITIVE_ENV_VARS:
                val = os.environ.get(var, "").strip()
                if val:
                    errors.append(
                        f"{_sanitize_env(var)} present in non-production environment — "
                        f"remove or unset before live execution"
                    )

        # 5. Compile result
        result.safe = len(errors) == 0 and result.controlled_live_enabled
        result.errors = errors

        if not result.safe:
            self._record_audit(
                "environment_safety_blocked",
                details={
                    "safe": False,
                    "environment": app_env or "not_set",
                    "errors": errors[:5],
                },
                severity="critical",
            )
        else:
            self._record_audit(
                "environment_safe",
                details={"environment": app_env},
                severity="info",
            )

        return result

    def check_or_raise(self) -> EnvironmentSafetyResult:
        """Run checks and raise EnvironmentSafetyError if not safe."""
        result = self.check()
        if not result.safe:
            raise EnvironmentSafetyError(
                f"Environment safety check failed: {'; '.join(result.errors[:3])}"
            )
        return result

    def _record_audit(self, event_type: str, details: dict | None = None,
                      severity: str = "info") -> None:
        if not self._audit_log:
            return
        self._audit_log.record(
            event_type, severity=severity,
            actor="environment_safety",
            details={"component": "environment_safety", **(details or {})},
        )


class EnvironmentSafetyError(Exception):
    """Raised when environment safety check fails."""
    pass
