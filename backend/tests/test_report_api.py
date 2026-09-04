from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.models import Base, User, Resume, SavedReport
from app.dependencies import get_db, get_current_user
from app.routers import jobs


def test_report_access():
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool
    )
    app = FastAPI()
    app.include_router(jobs.router)
    current = {'id': 1}

    def test_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(**current)

    try:
        with engine.begin() as conn:
            conn.exec_driver_sql('PRAGMA foreign_keys=ON')
            Base.metadata.create_all(conn)

        with Session(engine) as db:
            for i in (1, 2):
                db.add(User(
                    id=i, username=f'user{i}',
                    email=f'user{i}@example.com', password='test-only'
                ))
                db.flush()
                db.add(Resume(
                    id=i, user_id=i, original_filename=f'{i}.pdf',
                    stored_filename=f'{i}.pdf',
                    content_type='application/pdf', file_size=1
                ))
                db.flush()
                db.add(SavedReport(
                    id=i, user_id=i, resume_id=i,
                    title=f'岗位{i}', company='测试公司', jd='测试岗位原文',
                    content={'needs': [], 'checks': [], 'proofs': [f'用户{i}资料']}
                ))
            db.commit()

        with TestClient(app) as client:
            for user_id, other_id in ((1, 2), (2, 1)):
                current['id'] = user_id

                response = client.get('/jobs/reports')
                assert response.status_code == 200, response.text
                rows = response.json()
                assert [row['id'] for row in rows] == [user_id]
                assert set(rows[0]) == {'id', 'title', 'company', 'created_at'}

                response = client.get(f'/jobs/reports/{user_id}')
                assert response.status_code == 200, response.text
                assert response.json()['content']['proofs'] == [f'用户{user_id}资料']

                assert client.get(f'/jobs/reports/{other_id}').status_code == 404
                assert client.get('/jobs/reports/999').status_code == 404

                response = client.get('/jobs/reports?offset=1')
                assert response.status_code == 200
                assert response.json() == []
                assert client.get('/jobs/reports?offset=-1').status_code == 422
    finally:
        app.dependency_overrides.clear()
        engine.dispose()