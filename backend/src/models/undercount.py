from sqlalchemy import String, JSON, Double, ForeignKey, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class UndercountStudy(Base):
    __tablename__ = 'undercount_studies'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    dataset_id: Mapped[int] = mapped_column(ForeignKey('datasets.id'))
    dataset_checksum: Mapped[str] = mapped_column(String(64))
    zone: Mapped[str] = mapped_column(String(80), default='全部')
    idempotency_key: Mapped[str] = mapped_column(String(80), unique=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    direction: Mapped[str] = mapped_column(String(20), default='')
    error: Mapped[str] = mapped_column(String(1000), default='')
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[float] = mapped_column(Double)
class UndercountRevision(Base):
    __tablename__ = 'undercount_revisions'
    id: Mapped[int] = mapped_column(primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey('undercount_studies.id'))
    revision: Mapped[int] = mapped_column(Integer)
    caps: Mapped[dict] = mapped_column(JSON, default=dict)
    batch_cap: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    direction: Mapped[str] = mapped_column(String(20), default='')
    conclusion: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str] = mapped_column(String(1000), default='')
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[str] = mapped_column(String(150), default='')
    approved_at: Mapped[float | None] = mapped_column(Double, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[float] = mapped_column(Double)
