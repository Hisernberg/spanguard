"""Gateway configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    mode: str = "fast"                    # rules | fast | audit
    model_id: str | None = None
    threshold: float = 0.5
    upstream_url: str = "https://inference.baseten.co/v1"
    upstream_model: str = "meta-models/muse-spark-open-1026"
    upstream_api_key: str = ""            # BASETEN_API_KEY / META_API_KEY
    inspect_system: bool = True           # also inspect the system prompt
    inspect_user: bool = True             # also inspect user messages
    passthrough_assistant: bool = True    # never rewrite assistant history
    host: str = "127.0.0.1"
    port: int = 8819
    api_token: str = ""                   # optional bearer for exposing the gateway
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            mode=os.environ.get("SPANGUARD_MODE", "fast"),
            model_id=os.environ.get("SPANGUARD_MODEL") or None,
            threshold=float(os.environ.get("SPANGUARD_THRESHOLD", "0.5")),
            upstream_url=os.environ.get("SPANGUARD_UPSTREAM_URL", "https://inference.baseten.co/v1"),
            upstream_model=os.environ.get("SPANGUARD_UPSTREAM_MODEL", "meta-models/muse-spark-open-1026"),
            upstream_api_key=os.environ.get("BASETEN_API_KEY") or os.environ.get("META_API_KEY", ""),
            inspect_system=os.environ.get("SPANGUARD_INSPECT_SYSTEM", "1") == "1",
            inspect_user=os.environ.get("SPANGUARD_INSPECT_USER", "1") == "1",
            host=os.environ.get("SPANGUARD_HOST", "127.0.0.1"),
            port=int(os.environ.get("SPANGUARD_PORT", "8819")),
            api_token=os.environ.get("SPANGUARD_API_TOKEN", ""),
        )
