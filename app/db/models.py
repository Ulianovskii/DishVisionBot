# app/db/models.py
from datetime import datetime, date

import sqlalchemy as sa
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base




# 4.1. Таблица users
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(sa.BigInteger, unique=True, nullable=False, index=True)
    is_premium: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text("FALSE"))
    premium_until: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    # 🔽 НОВАЯ СТРОКА
    paid_photos_balance: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="0")

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )


# 4.2. Таблица user_limits
class UserLimit(Base):
    __tablename__ = "user_limits"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="user_limits_unique"),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    photos_used: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="0")
    refinements_used: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="0")


# 4.3. Таблица meals
class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    eaten_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    title: Mapped[str] = mapped_column(sa.Text, nullable=False)
    weight_grams: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    calories: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    proteins: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    fats: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    carbs: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    source_message_id: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )


# 4.4. Таблица calorie_plans
class CaloriePlan(Base):
    __tablename__ = "calorie_plans"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    daily_target: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )


# 4.5. Таблица promo_codes
class PromoCode(Base):
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(sa.Text, unique=True, nullable=False, index=True)
    days: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    max_activations: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="1")
    activations: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="0")
    expires_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_by: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )


# 4.6. Таблица promo_code_activations
class PromoCodeActivation(Base):
    __tablename__ = "promo_code_activations"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    promo_code_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        ForeignKey("promo_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    activated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )


# 4.7. Таблица promo_bans
class PromoBan(Base):
    __tablename__ = "promo_bans"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    banned_until: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )


# 4.8. Таблица admin_users
class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(sa.BigInteger, unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )


# 4.9. Таблица gpt_usage_stats
class GPTUsageStat(Base):
    __tablename__ = "gpt_usage_stats"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="gpt_usage_unique"),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    tokens_prompt: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="0")
    tokens_completion: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="0")
    cost_usd: Mapped[float] = mapped_column(
        sa.Numeric(10, 4),
        nullable=False,
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
