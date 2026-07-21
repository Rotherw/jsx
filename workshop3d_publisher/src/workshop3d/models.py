"""Core data types: product states and the persisted product record."""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


class State(str, Enum):
    """Lifecycle states a product moves through (spec section 4)."""

    DETECTED = "DETECTED"
    WAITING_FOR_REQUIRED_FILES = "WAITING_FOR_REQUIRED_FILES"
    VALIDATING = "VALIDATING"
    PREPARING_PRODUCT = "PREPARING_PRODUCT"
    PREPARING_MEDIA = "PREPARING_MEDIA"
    READY_TO_PUBLISH = "READY_TO_PUBLISH"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    PROMOTING = "PROMOTING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    NEEDS_ATTENTION = "NEEDS_ATTENTION"
    FAILED = "FAILED"


# Terminal states: the pipeline will not automatically re-run from these.
TERMINAL_STATES = {
    State.COMPLETED,
    State.COMPLETED_WITH_WARNINGS,
    State.NEEDS_ATTENTION,
    State.FAILED,
}


@dataclass
class StoreResult:
    """Outcome of publishing to a single store."""

    platform: str
    status: str = "PENDING"          # PENDING | PUBLISHED | DRY_RUN | NOT_CONNECTED | FAILED | SKIPPED
    listing_id: Optional[str] = None
    url: Optional[str] = None
    message: str = ""


@dataclass
class SocialResult:
    """Outcome of a single social-media post."""

    platform: str
    status: str = "PENDING"          # PENDING | POSTED | DRY_RUN | NOT_CONNECTED | FAILED | SKIPPED
    post_url: Optional[str] = None
    message: str = ""


@dataclass
class ProductRecord:
    """Everything we persist about one product (spec sections 4 & 15).

    Persisting this lets the program restart without losing progress and
    guarantees idempotent, duplicate-free processing.
    """

    product_id: str
    folder_name: str
    folder_path: str
    state: str = State.DETECTED.value
    detected_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    # Detected files (relative names).
    png_files: list[str] = field(default_factory=list)
    stl_files: list[str] = field(default_factory=list)
    glb_files: list[str] = field(default_factory=list)
    tmf_files: list[str] = field(default_factory=list)   # .3mf

    # Content-hash of every file -> used as the product identity / dedup key.
    checksums: dict[str, str] = field(default_factory=dict)

    # Generated artefacts.
    fact_card: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    media: list[str] = field(default_factory=list)
    package_path: Optional[str] = None

    # Publication outcomes.
    stores: dict[str, dict] = field(default_factory=dict)      # platform -> StoreResult dict
    social: dict[str, dict] = field(default_factory=dict)      # platform -> SocialResult dict
    links: dict[str, str] = field(default_factory=dict)
    main_link: Optional[str] = None

    # Bookkeeping.
    attempts: int = 0
    error_history: list[str] = field(default_factory=list)
    required_user_action: Optional[str] = None

    def touch(self) -> None:
        self.updated_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ProductRecord":
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})
