import uuid
import enum
from datetime import datetime
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Boolean,
    Numeric,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.vulnerability import Vendor, Product, Cwe


class KevRequirement(str, enum.Enum):
    NONE = "NONE"
    REQUIRED = "REQUIRED"


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)

    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    min_cvss: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    min_epss: Mapped[float | None] = mapped_column(Numeric(10, 5), nullable=True)
    kev_requirement: Mapped[KevRequirement] = mapped_column(
        Enum(KevRequirement, name="kevrequirement"),
        default=KevRequirement.NONE,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    user: Mapped["User"] = relationship()
    cves: Mapped[list["WatchlistCve"]] = relationship(
        back_populates="watchlist", cascade="all, delete-orphan"
    )
    vendors: Mapped[list["WatchlistVendor"]] = relationship(
        back_populates="watchlist", cascade="all, delete-orphan"
    )
    products: Mapped[list["WatchlistProduct"]] = relationship(
        back_populates="watchlist", cascade="all, delete-orphan"
    )
    keywords: Mapped[list["WatchlistKeyword"]] = relationship(
        back_populates="watchlist", cascade="all, delete-orphan"
    )
    cwes: Mapped[list["WatchlistCwe"]] = relationship(
        back_populates="watchlist", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_watchlist_name"),
        # Unique constraint for composite FK from AlertRule
        UniqueConstraint("id", "user_id", name="uq_watchlist_id_user_id"),
    )


class WatchlistCve(Base):
    __tablename__ = "watchlist_cves"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    watchlist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cve_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    watchlist: Mapped["Watchlist"] = relationship(back_populates="cves")

    __table_args__ = (
        UniqueConstraint("watchlist_id", "cve_id", name="uq_watchlist_cve"),
    )


class WatchlistVendor(Base):
    __tablename__ = "watchlist_vendors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    watchlist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    watchlist: Mapped["Watchlist"] = relationship(back_populates="vendors")
    vendor: Mapped["Vendor"] = relationship()

    __table_args__ = (
        UniqueConstraint("watchlist_id", "vendor_id", name="uq_watchlist_vendor"),
    )


class WatchlistProduct(Base):
    __tablename__ = "watchlist_products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    watchlist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    watchlist: Mapped["Watchlist"] = relationship(back_populates="products")
    product: Mapped["Product"] = relationship()

    __table_args__ = (
        UniqueConstraint("watchlist_id", "product_id", name="uq_watchlist_product"),
    )


class WatchlistKeyword(Base):
    __tablename__ = "watchlist_keywords"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    watchlist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    watchlist: Mapped["Watchlist"] = relationship(back_populates="keywords")

    __table_args__ = (
        UniqueConstraint("watchlist_id", "keyword", name="uq_watchlist_keyword"),
    )


class WatchlistCwe(Base):
    __tablename__ = "watchlist_cwes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    watchlist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cwe_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cwes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    watchlist: Mapped["Watchlist"] = relationship(back_populates="cwes")
    cwe: Mapped["Cwe"] = relationship()

    __table_args__ = (
        UniqueConstraint("watchlist_id", "cwe_id", name="uq_watchlist_cwe_id"),
    )
