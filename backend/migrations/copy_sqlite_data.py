from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import SessionLocal as NewSession
from app.models import User, Job, Resume, ResumeAnalysis, SavedReport, Application

old_file = Path(__file__).resolve().parents[1] / 'jobs.db'
old_engine = create_engine(f"sqlite:///{old_file.as_posix()}")
OldSession = sessionmaker(bind=old_engine)
models = [Job, User, Resume, ResumeAnalysis, SavedReport, Application]

# 新建迁移脚本

def copy_data():
    old_db = OldSession()
    new_db = NewSession()
    try:
        for model in models:
            for row in old_db.query(model).all():
                data = {col.name:getattr(row,col.name) for col in model.__table__.columns}
                new_db.merge(model(**data))
            new_db.flush()
    # flush() 发送 SQL，但不结束事务。
        new_db.commit()
    except Exception:
        new_db.rollback()
        raise
    finally:
        old_db.close()
        new_db.close()

if __name__ == '__main__':
    copy_data()