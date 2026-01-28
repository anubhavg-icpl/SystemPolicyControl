"""Shared data models for SystemPolicyControl using dataclasses."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class SystemPolicy:
    allow_identified_developers: bool = True
    enable_assessment: bool = True
    enable_xprotect_malware_upload: bool = True
    profile_identifier: str = "com.systempolicycontrol.policy"
    display_name: str = "System Policy Control"
    organization: str = "SystemPolicyControl"
    description: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.enable_assessment:
            self.allow_identified_developers = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "SystemPolicy":
        filtered: Dict[str, Any] = {}
        for field_name in cls.__dataclass_fields__.keys():  # type: ignore[attr-defined]
            if field_name in payload:
                filtered[field_name] = payload[field_name]
        return cls(**filtered)


@dataclass
class PolicyState:
    policy: SystemPolicy
    profile_path: str
    applied_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    install_attempted: bool = True
    install_succeeded: bool = False
    installer_stdout: Optional[str] = None
    installer_stderr: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["applied_at"] = self.applied_at.isoformat()
        data["policy"] = self.policy.to_dict()
        return data

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "PolicyState":
        payload = payload.copy()
        payload["policy"] = SystemPolicy.from_dict(payload["policy"])
        timestamp = payload["applied_at"]
        if isinstance(timestamp, str) and timestamp.endswith("Z"):
            timestamp = timestamp[:-1] + "+00:00"
        payload["applied_at"] = datetime.fromisoformat(timestamp)
        return cls(**payload)
