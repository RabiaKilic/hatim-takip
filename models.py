from sqlalchemy import String, DateTime, ForeignKey, Boolean, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class Hatim(Base):
    __tablename__ = "hatims"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Kimin adına / hangi vesileyle başlatıldığı
    name: Mapped[str] = mapped_column(String(200))

    # Hatmi başlatan kullanıcı
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    # Kullanıcının belirlediği başlama zamanı
    start_date: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Kullanıcının belirlediği hedef bitiş zamanı
    end_date: Mapped[datetime | None] = mapped_column(nullable=True)

    # "aktif" ya da "tamamlandi"
    durum: Mapped[str] = mapped_column(String(20), default="aktif")

    # Tüm cüzler okunduğunda gerçekte tamamlandığı an
    tamamlanma_tarihi: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )


class Cuz(Base):
    __tablename__ = "cuzler"

    __table_args__ = (
        UniqueConstraint(
            "hatim_id",
            "cuz_no",
            name="uq_hatim_cuz_no"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # Cüzün atandığı kullanıcı
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    # Cüzün ait olduğu hatim
    hatim_id: Mapped[int] = mapped_column(
        ForeignKey("hatims.id")
    )

    # 1-30 arası cüz numarası
    cuz_no: Mapped[int] = mapped_column(Integer)

    # Okundu mu?
    okundu: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )

    # Okunduğu tarih
    okunma_tarihi: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    # Cüzün atanma tarihi
    atanma_tarihi: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )