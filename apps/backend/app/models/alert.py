import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Numeric, ForeignKey, CheckConstraint, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base
import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.watchlist import Watchlist
    from app.models.vulnerability import Vulnerability


class AlertAction(str, enum.Enum):
    EMAIL = "email"
    WEBHOOK = "webhook"


class AlertEventStatus(str, enum.Enum):
    UNREAD = "unread"
    READ = "read"
    DISMISSED = "dismissed"


class DeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    watchlist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cvss_threshold: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    action: Mapped[AlertAction] = mapped_column(Enum(AlertAction), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    user: Mapped["User"] = relationship()
    watchlist: Mapped["Watchlist"] = relationship()
    events: Mapped[list["AlertEvent"]] = relationship(
        back_populates="rule", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "cvss_threshold >= 0.0 AND cvss_threshold <= 10.0",
            name="chk_rule_cvss_threshold",
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
    status: Mapped[AlertEventStatus] = mapped_column(
        Enum(AlertEventStatus), default=AlertEventStatus.UNREAD, nullable=False
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
        Enum(AlertAction), nullable=False
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus), default=DeliveryStatus.PENDING, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    event: Mapped["AlertEvent"] = relationship(back_populates="deliveries")
