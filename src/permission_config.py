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
        with open(path) as f:
            data = json.load(f)

        profile_name = data.get("profile_name", path.stem)
        permissions = []
        for entry in data.get("permissions", []):
            category = PermissionCategory(entry["category"])
            scope = PermissionScope(entry["scope"])
            details = entry.get("details", "")
            permissions.append(Permission(category, scope, details))

        return cls(permissions, profile_name)

    @classmethod
    def from_dict(cls, data: dict) -> PermissionConfig:
        """Load a permission configuration from a dictionary."""
        profile_name = data.get("profile_name", "default")
        permissions = []
        for entry in data.get("permissions", []):
            category = PermissionCategory(entry["category"])
            scope = PermissionScope(entry["scope"])
            details = entry.get("details", "")
            permissions.append(Permission(category, scope, details))

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
