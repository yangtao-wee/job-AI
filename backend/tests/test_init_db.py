from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import init_db
from app.models import Base, Job


def test_seed_jobs_is_idempotent(monkeypatch):
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    make_session = sessionmaker(bind=engine)
    monkeypatch.setattr(init_db, 'SessionLocal', make_session)
    init_db.seed_jobs()
    init_db.seed_jobs()
    with make_session() as db:
        assert db.query(Job).count() == len(init_db.JOBS)