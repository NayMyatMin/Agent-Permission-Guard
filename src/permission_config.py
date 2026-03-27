"""Loads and represents agent permission configurations."""

from __future__ import annotations

import json
from pathlib import Path

from .models import Permission, PermissionCategory, PermissionScope


class PermissionConfig:
    """Represents the current permission configuration of an agent."""

    def __init__(self, permissions: list[Permission], profile_name: str = "default") -> None:
        self.permissions = permissions
        self.profile_name = profile_name
        self._by_category: dict[PermissionCategory, Permission] = {
            p.category: p for p in permissions
        }

    def get(self, category: PermissionCategory) -> Permission:
        """Get permission for a category, defaulting to DISABLED."""
        return self._by_category.get(
            category,
            Permission(category, PermissionScope.DISABLED, "Not configured"),
        )

    @property
    def active_permissions(self) -> list[Permission]:
        """Return only permissions that are not disabled."""
        return [p for p in self.permissions if p.is_active]

    @property
    def active_categories(self) -> set[PermissionCategory]:
        """Return categories with active (non-disabled) permissions."""
        return {p.category for p in self.active_permissions}

    def has_active(self, category: PermissionCategory) -> bool:
        """Check if a permission category is active."""
        return self.get(category).is_active

    @classmethod
    def from_json_file(cls, path: str | Path) -> PermissionConfig:
        """Load a permission configuration from a JSON file."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(
                f"Permission config file not found: {path}\n"
                f"Available configs should be in the configs/ directory."
            )

        with open(path) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in {path}: {e}") from e

        return cls._parse_config(data, fallback_name=path.stem)

    @classmethod
    def from_dict(cls, data: dict) -> PermissionConfig:
        """Load a permission configuration from a dictionary."""
        return cls._parse_config(data, fallback_name="default")

    @classmethod
    def _parse_config(cls, data: dict, fallback_name: str) -> PermissionConfig:
        """Parse and validate a config dictionary into a PermissionConfig."""
        if not isinstance(data, dict):
            raise ValueError("Config must be a JSON object.")

        profile_name = data.get("profile_name", fallback_name)
        raw_permissions = data.get("permissions", [])

        if not isinstance(raw_permissions, list):
            raise ValueError("'permissions' must be a list of permission entries.")

        permissions = []
        valid_categories = {e.value for e in PermissionCategory}
        valid_scopes = {e.value for e in PermissionScope}

        for i, entry in enumerate(raw_permissions):
            if not isinstance(entry, dict):
                raise ValueError(f"Permission entry {i} must be an object, got {type(entry).__name__}.")

            if "category" not in entry:
                raise ValueError(f"Permission entry {i} is missing required field 'category'.")
            if "scope" not in entry:
                raise ValueError(f"Permission entry {i} is missing required field 'scope'.")

            cat_val = entry["category"]
            scope_val = entry["scope"]

            if cat_val not in valid_categories:
                raise ValueError(
                    f"Permission entry {i}: unknown category '{cat_val}'. "
                    f"Valid: {', '.join(sorted(valid_categories))}"
                )
            if scope_val not in valid_scopes:
                raise ValueError(
                    f"Permission entry {i}: unknown scope '{scope_val}'. "
                    f"Valid: {', '.join(sorted(valid_scopes))}"
                )

            permissions.append(Permission(
                PermissionCategory(cat_val),
                PermissionScope(scope_val),
                entry.get("details", ""),
            ))

        return cls(permissions, profile_name)

    def to_dict(self) -> dict:
        """Serialize the configuration to a dictionary."""
        return {
            "profile_name": self.profile_name,
            "permissions": [
                {
                    "category": p.category.value,
                    "scope": p.scope.value,
                    "details": p.details,
                }
                for p in self.permissions
            ],
        }
