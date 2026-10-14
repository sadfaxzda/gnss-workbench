"""SQLite stores run metadata; immutable scientific records live alongside it."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import JSON, Integer, String, Text, cast, create_engine, func, or_, select, true
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .settings import PROJECT_ROOT


class Base(DeclarativeBase):
    pass


class RunRecord(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    created_at: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(24))
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON)
    epoch_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    def public(self) -> dict[str, Any]:
        return {
            key: getattr(self, key)
            for key in (
                "id",
                "created_at",
                "status",
                "configuration",
                "epoch_count",
                "summary",
                "error",
            )
        }


class RunStore:
    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{root / 'workbench.db'}"
        config = Config(str(PROJECT_ROOT / "alembic.ini"))
        config.set_main_option("sqlalchemy.url", url)
        command.upgrade(config, "head")
        self.engine = create_engine(url, connect_args={"check_same_thread": False})
        with Session(self.engine) as session:
            for record in session.scalars(
                select(RunRecord).where(RunRecord.status.in_(["running", "stopping"]))
            ):
                record.status = "interrupted"
                record.error = "服务重启，原计算进程已结束；可新建运行复现实验"
            session.commit()

    def create(self, run_id: str, created_at: str, configuration: dict[str, Any]) -> None:
        with Session(self.engine) as session:
            session.add(
                RunRecord(
                    id=run_id,
                    created_at=created_at,
                    configuration=configuration,
                    status="running",
                    epoch_count=0,
                    summary={},
                )
            )
            session.commit()

    def update(self, run_id: str, **fields: Any) -> None:
        with Session(self.engine) as session:
            record = session.get(RunRecord, run_id)
            if record is None:
                raise KeyError(run_id)
            for key, value in fields.items():
                setattr(record, key, value)
            session.commit()

    def get(self, run_id: str) -> dict[str, Any] | None:
        with Session(self.engine) as session:
            record = session.get(RunRecord, run_id)
            return record.public() if record else None

    @staticmethod
    def _matching(query: str):
        if not query:
            return true()
        return or_(
            RunRecord.id.contains(query, autoescape=True),
            cast(RunRecord.configuration, String).contains(query, autoescape=True),
        )

    def list(self, offset: int = 0, limit: int = 100, query: str = "") -> list[dict[str, Any]]:
        with Session(self.engine) as session:
            return [
                r.public()
                for r in session.scalars(
                    select(RunRecord)
                    .where(self._matching(query))
                    .order_by(RunRecord.created_at.desc(), RunRecord.id.desc())
                    .offset(offset)
                    .limit(limit)
                )
            ]

    def count(self, query: str = "") -> int:
        with Session(self.engine) as session:
            return (
                session.scalar(
                    select(func.count()).select_from(RunRecord).where(self._matching(query))
                )
                or 0
            )

    def close(self) -> None:
        self.engine.dispose()
