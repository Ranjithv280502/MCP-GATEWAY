from dataclasses import dataclass, field
from typing import Any


@dataclass
class CollisionRegistry:
    separator: str = "."
    _original_to_namespaced: dict[tuple[str, str], str] = field(default_factory=dict)
    _namespaced_to_original: dict[str, tuple[str, str, str]] = field(default_factory=dict)
    _collision_log: list[dict] = field(default_factory=list)

    def register(self, server_id: str, namespace: str, original_name: str) -> str:
        key = (server_id, original_name)
        if key in self._original_to_namespaced:
            return self._original_to_namespaced[key]
        namespaced = f"{namespace}{self.separator}{original_name}"
        if namespaced in self._namespaced_to_original:
            existing_server, existing_ns, existing_orig = self._namespaced_to_original[namespaced]
            suffix = 2
            while True:
                candidate = f"{namespace}{self.separator}{original_name}_{suffix}"
                if candidate not in self._namespaced_to_original:
                    namespaced = candidate
                    break
                suffix += 1
            self._collision_log.append({
                "original_name": original_name,
                "servers": [existing_server, server_id],
                "resolved_as": namespaced,
            })
        self._original_to_namespaced[key] = namespaced
        self._namespaced_to_original[namespaced] = (server_id, namespace, original_name)
        return namespaced

    def resolve(self, namespaced_name: str) -> tuple[str, str, str] | None:
        return self._namespaced_to_original.get(namespaced_name)

    def get_collisions(self) -> list[dict]:
        return list(self._collision_log)

    def namespace_tool(self, tool: dict[str, Any], server_id: str, namespace: str) -> dict[str, Any]:
        original = tool["name"]
        namespaced = self.register(server_id, namespace, original)
        return {
            **tool,
            "name": namespaced,
            "original_name": original,
            "server_id": server_id,
            "namespace": namespace,
        }
