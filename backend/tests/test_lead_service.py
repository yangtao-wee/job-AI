from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from unittest.mock import MagicMock
import pytest
from app.models import Base, JobLead
from app.services.lead_service import update_status, save_leads
from app.schemas import LeadIn

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