from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from unittest.mock import MagicMock
import pytest
from app.models import Base, JobLead
from app.services.lead_service import update_status, save_leads, mark_above
from app.schemas import LeadIn
from app.services import lead_service as service

def test_update_status_isolated():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        lead = JobLead(user_id=1, title='Python', company='A', url='https://test/1')
        db.add(lead); db.commit(); db.refresh(lead)
        assert update_status(db, 2, lead.id, '已投递') is None
        db.refresh(lead)
        assert lead.status == '新抓取'
        assert update_status(db, 1, lead.id, '已投递').status == '已投递'

def test_update_status_rolls_back():
    db = MagicMock()
    lead = MagicMock(status='新抓取')
    db.query.return_value.filter.return_value.first.return_value = lead
    db.commit.side_effect = SQLAlchemyError('commit failed')

    with pytest.raises(SQLAlchemyError):
        update_status(db, 1, 1, '已投递')

    db.rollback.assert_called_once()
    db.refresh.assert_not_called()

def test_save_leads_is_idempotent():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        first = LeadIn(title='Python', company='A', url='https://test/1', quick_score=60)
        higher = LeadIn(title='Python', company='A', url='https://test/1', quick_score=80)

        assert save_leads(db, 1, [first]) == {'added': 1, 'updated': 0, 'total': 1}
        assert save_leads(db, 1, [higher]) == {'added': 0, 'updated': 1, 'total': 1}
        rows = db.query(JobLead).all()
        assert len(rows) == 1
        assert rows[0].quick_score == 80

def test_analyze_next_keeps_one_transaction(monkeypatch):
    db=MagicMock()
    base=db.query.return_value.filter.return_value
    job=MagicMock(
        jd_text='负责Python后端、AI应用工程和系统稳定性建设工作。',
        title='Python开发',company='A'
    )
    base.order_by.return_value.first.return_value=job
    result=MagicMock(checks=[])
    monkeypatch.setattr(service,'make_report',lambda *args:result)
    save=MagicMock(return_value=MagicMock(id=9))
    monkeypatch.setattr(service,'save_report',save)
    service.analyze_next(db,1,2,['proof'])
    assert save.call_args.kwargs['commit'] is False
    assert job.report_id==9
    db.commit.assert_called_once()

def make_db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return Session(engine)


def test_mark_above_only_touches_new():
    with make_db() as db:
        db.add_all([
            JobLead(user_id=1, title='高分', url='u1', quick_score=80),
            JobLead(user_id=1, title='刚好', url='u2', quick_score=60),
            JobLead(user_id=1, title='低分', url='u3', quick_score=30),
            JobLead(user_id=1, title='已跳过的高分', url='u4',
                    quick_score=90, status='已跳过'),
            JobLead(user_id=2, title='别人的高分', url='u5', quick_score=95),
        ])
        db.commit()

        assert mark_above(db, 1, 60) == 2

        got = {r.url: r.status for r in db.query(JobLead).all()}
        assert got['u1'] == '待投递'
        assert got['u2'] == '待投递'
        assert got['u3'] == '新抓取'
        assert got['u4'] == '已跳过'
        assert got['u5'] == '新抓取'