import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    String,
    DateTime,
    Numeric,
    ForeignKey,
    CheckConstraint,
    Enum,
    Boolean,
    Integer,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.watchlist import Watchlist
    from app.models.vulnerability import Vulnerability


class AlertAction(str, enum.Enum):
    IN_APP_NOTIFICATION = "IN_APP_NOTIFICATION"
    WEBHOOK = "WEBHOOK"


class AlertEventStatus(str, enum.Enum):
    UNREAD = "unread"
    READ = "read"
    DISMISSED = "dismissed"


class DeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    user: Mapped["User"] = relationship()


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    watchlist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rule_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    cvss_threshold: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    epss_condition: Mapped[float | None] = mapped_column(Numeric(10, 5), nullable=True)
    kev_condition: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Store these as simple JSON arrays of strings for Phase 1
    cwe_condition: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    keyword_condition: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    trigger_events: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )

    action: Mapped[AlertAction] = mapped_column(
        Enum(AlertAction, name="alertaction"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    user: Mapped["User"] = relationship()
    watchlist: Mapped["Watchlist"] = relationship(overlaps="user")
    events: Mapped[list["AlertEvent"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "cvss_threshold >= 0.0 AND cvss_threshold <= 10.0",
            name="chk_rule_cvss_threshold",
        ),
        # Ensure that the watchlist belongs to the exact same user as the alert rule
        ForeignKeyConstraint(
            ["watchlist_id", "user_id"],
            ["watchlists.id", "watchlists.user_id"],
            ondelete="CASCADE",
        ),
    )


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("alert_rules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vulnerability_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vulnerabilities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    deduplication_key: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False
    )

    status: Mapped[AlertEventStatus] = mapped_column(
        Enum(AlertEventStatus, name="alerteventstatus"),
        default=AlertEventStatus.UNREAD,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    rule: Mapped["AlertRule"] = relationship(back_populates="events")
    vulnerability: Mapped["Vulnerability"] = relationship()
    deliveries: Mapped[list["NotificationDelivery"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("alert_events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    delivery_method: Mapped[AlertAction] = mapped_column(
        Enum(AlertAction, name="alertaction", create_type=False), nullable=False
    )
    webhook_endpoint_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("webhook_endpoints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, name="deliverystatus"),
        default=DeliveryStatus.PENDING,
        nullable=False,
    )

    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_terminal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    event: Mapped["AlertEvent"] = relationship(back_populates="deliveries")
    webhook_endpoint: Mapped["WebhookEndpoint | None"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "idempotency_key",
            name="uq_delivery_idempotency_key",
            postgresql_nulls_not_distinct=True,
        ),
    )
