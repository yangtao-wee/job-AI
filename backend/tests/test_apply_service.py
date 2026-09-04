from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models import Base, User, Resume, SavedReport, Application
from app.services.apply_service import create_apply,list_apply,update_apply
from app.schemas import ApplyUpdate


def test_create_apply():
    engine = create_engine('sqlite:///:memory:')
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all([
                User(id=1, username='u1', email='u1@test.com', password='test'),
                User(id=2, username='u2', email='u2@test.com', password='test')
            ])
            db.flush()
            db.add_all([
                Resume(id=1, user_id=1, original_filename='a.pdf',
                       stored_filename='a.pdf', content_type='application/pdf', file_size=1),
                Resume(id=2, user_id=2, original_filename='b.pdf',
                       stored_filename='b.pdf', content_type='application/pdf', file_size=1)
            ])
            db.flush()
            db.add_all([
                SavedReport(id=1, user_id=1, resume_id=1, title='Python',
                            company='A', jd='Python岗位要求', content={}),
                SavedReport(id=2, user_id=2, resume_id=2, title='Vue',
                            company='B', jd='Vue岗位要求', content={})
            ])
            db.commit()

            first = create_apply(db, 1, 1)
            assert first.status == '待投递'
            assert first.user_id == 1
            assert first.report_id == 1

            again = create_apply(db, 1, 1)
            assert again.id == first.id
            assert db.query(Application).count() == 1

            denied = create_apply(db, 1, 2)
            assert denied is None
            assert db.query(Application).count() == 1
            data = ApplyUpdate(status='面试中', note='周五面试')
            changed = update_apply(db, 1, first.id, data)
            assert changed.status == '面试中'
            db.rollback()
            rows = list_apply(db, 1)
            assert len(rows) == 1
            assert (rows[0].title, rows[0].company) == ('Python', 'A')
            assert (rows[0].status, rows[0].note) == ('面试中', '周五面试')
            assert list_apply(db, 2) == []
            other = ApplyUpdate(status='已结束', note='越权修改')
            assert update_apply(db, 2, first.id, other) is None
            assert update_apply(db, 1, 999, other) is None
            db.refresh(first)
            assert (first.status, first.note) == ('面试中', '周五面试')
    finally:
        engine.dispose()