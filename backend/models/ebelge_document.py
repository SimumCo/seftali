"""MongoDB model for ebelge_documents collection.

Bu koleksiyon e-Fatura ve e-İrsaliye belgelerinin **lokal ızini** tutar.
API key veya hassas header bilgisi ASLA burada saklanmaz.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field


class EBelgeDocumentType(str, Enum):
    EFATURA = "efatura"
    EIRSALIYE = "eirsaliye"


class EBelgeInternalStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"
    UNKNOWN = "unknown"


class EBelgeDocument(BaseModel):
    """Internal DB representation of an outbound e-Belge document attempt."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_type: EBelgeDocumentType
    provider: str = "turkcell"
    provider_id: Optional[str] = None
    document_number: Optional[str] = None
    local_reference_id: Optional[str] = None

    receiver_vkn: Optional[str] = None
    receiver_name: Optional[str] = None
    receiver_alias: Optional[str] = None

    status_internal: EBelgeInternalStatus = EBelgeInternalStatus.DRAFT
    provider_status: Optional[str] = None
    provider_message: Optional[str] = None
    trace_id: Optional[str] = None

    # Snapshotlar (secret redacted)
    request_payload_snapshot: Optional[Dict[str, Any]] = None
    response_payload_snapshot: Optional[Dict[str, Any]] = None

    created_by: Optional[str] = None  # user.id
    created_by_username: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
