import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.base import Base
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.vulnerability import Vendor, Product


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

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_watchlist_name"),
    )


class WatchlistCve(Base):
    __tablename__ = "watchlist_cves"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    watchlist_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    cve_id: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # Intentionally not a FK to vulnerabilities table to allow watching unknown CVEs
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
