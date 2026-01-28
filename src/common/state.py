"""Persistence helpers for tracking the latest Gatekeeper profile."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .models import PolicyState


class PolicyStateStore:
    """Lightweight JSON-backed store for policy runs."""

    def __init__(self, path: Path | str = Path("data/policy_state.json")) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Optional[PolicyState]:
        if not self.path.exists():
            return None
        with self.path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return PolicyState.from_dict(payload)

    def save(self, state: PolicyState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(state.to_dict(), handle, indent=2, sort_keys=True)
