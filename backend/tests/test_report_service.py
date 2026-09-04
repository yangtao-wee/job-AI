import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models import Base, User, Resume, SavedReport
from app.schemas import JobAssistRequest, Report, Need, Check
from app.services.report_service import save_report


def test_save_report():
    engine = create_engine('sqlite:///:memory:')
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql('PRAGMA foreign_keys=ON')
            Base.metadata.create_all(conn)

        request = JobAssistRequest(
            resume_id=1, job_title='Python开发', company='测试公司',
            jd_text='岗位要求使用Python开发后端接口，并维护已有业务功能。'
        )
        result = Report(
            needs=[Need(id=0, text='开发接口', kind='职责', quote='开发后端接口')],
            checks=[Check(need_id=0, status='有依据', proof_ids=[0], note='有接口经历')],
            proofs=['使用Python开发接口。']
        )
        expected = result.model_dump(mode='json')

        with Session(engine) as db:
            db.add(User(id=1, username='test', email='test@example.com', password='test-only'))
            db.flush()
            db.add(Resume(
                id=1, user_id=1, original_filename='test.pdf',
                stored_filename='test.pdf', content_type='application/pdf', file_size=1
            ))
            db.commit()

            save_report(db, 1, request, result)

            with pytest.raises(IntegrityError):
                save_report(db, 999, request, result)

            result.proofs[0] = '使用Python维护接口。'
            save_report(db, 1, request, result)

        with Session(engine) as db:
            rows = db.query(SavedReport).order_by(SavedReport.id).all()
            assert len(rows) == 2
            assert rows[0].user_id == 1
            assert rows[0].resume_id == 1
            assert rows[0].title == request.job_title
            assert rows[0].company == request.company
            assert rows[0].jd == request.jd_text
            assert rows[0].created_at is not None
            assert rows[0].content == expected
            assert rows[1].content == result.model_dump(mode='json')
    finally:
        engine.dispose()