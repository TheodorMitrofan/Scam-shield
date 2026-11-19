"""Engine / session handling. One `Database` lives on `app.state.db` (tests swap in SQLite)."""

import logging
from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event, select, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import APPLICATIONS, ATTRIBUTES, Application, AttributeDefinition, Base

log = logging.getLogger(__name__)


class Database:
    def __init__(self, url: str) -> None:
        kwargs: dict = {"pool_pre_ping": True}
        if url.startswith("sqlite"):
            kwargs = {"connect_args": {"check_same_thread": False}}
            if ":memory:" in url or url == "sqlite://":
                kwargs["poolclass"] = StaticPool
        self.engine: Engine = create_engine(url, **kwargs)
        if url.startswith("sqlite"):
            # SQLite ignores ON DELETE CASCADE unless foreign keys are switched on per connection.
            event.listen(self.engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
        self.sessionmaker = sessionmaker(self.engine, expire_on_commit=False)
        self.ready = False

    def init(self) -> bool:
        """Create tables + seed lookup rows + purge expired data. Never raises: the app must start
        (and analyse without saving) even when PostgreSQL is down."""
        try:
            Base.metadata.create_all(self.engine)
            with self.sessionmaker.begin() as s:
                _seed(s)
                from .repository import purge_expired  # local import: repository imports this module

                purge_expired(s)
            self.ready = True
        except Exception as e:  # noqa: BLE001
            log.warning("database unavailable, saving disabled: %s", e)
            self.ready = False
        return self.ready

    def ping(self) -> bool:
        try:
            with self.engine.connect() as c:
                c.execute(text("SELECT 1"))
            if not self.ready:
                return self.init()
            return True
        except Exception:  # noqa: BLE001
            return False

    def session(self) -> Iterator[Session]:
        with self.sessionmaker() as s:
            yield s


def _seed(s: Session) -> None:
    existing = {a.code: a for a in s.scalars(select(Application))}
    for code, name, kind in APPLICATIONS:
        if code not in existing:
            existing[code] = Application(code=code, display_name=name, view_kind=kind)
            s.add(existing[code])
    s.flush()
    have = {(d.application_id, d.entity, d.name) for d in s.scalars(select(AttributeDefinition))}
    for app_code, entity, name, dtype in ATTRIBUTES:
        app_id = existing[app_code].id if app_code else None
        if (app_id, entity, name) not in have:
            s.add(AttributeDefinition(application_id=app_id, entity=entity, name=name, data_type=dtype))
