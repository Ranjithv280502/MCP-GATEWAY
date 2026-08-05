import fnmatch
from dataclasses import dataclass, field

import yaml

from gateway.config import get_settings


@dataclass
class RBACPolicy:
    roles: dict[str, dict]
    users: dict[str, dict]

    @classmethod
    def load(cls, path: str = "config/rbac_policy.yaml") -> "RBACPolicy":
        settings = get_settings()
        with open(settings.project_root / path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(roles=data.get("roles", {}), users=data.get("users", {}))

    def get_user_roles(self, email: str) -> list[str]:
        user = self.users.get(email, {})
        return user.get("roles", [])

    def is_allowed(self, email: str, tool_name: str) -> tuple[bool, str]:
        roles = self.get_user_roles(email)
        if not roles:
            return False, "no roles assigned"
        for role_name in roles:
            role = self.roles.get(role_name, {})
            patterns = role.get("allowed_tools", [])
            for pattern in patterns:
                if pattern == "*":
                    return True, f"allowed by role '{role_name}' (wildcard)"
                if fnmatch.fnmatch(tool_name, pattern):
                    return True, f"allowed by role '{role_name}' pattern '{pattern}'"
        return False, f"denied: no matching pattern for roles {roles}"


@dataclass
class ToolRecord:
    namespaced_name: str
    original_name: str
    server_id: str
    namespace: str
    description: str
    input_schema: dict = field(default_factory=dict)
