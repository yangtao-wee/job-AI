from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from ..models import Application,SavedReport
from ..schemas import ApplyUpdate

def create_apply(db:Session,user_id:int,report_id:int):
    report=db.query(SavedReport).filter(
        SavedReport.id==report_id,
        SavedReport.user_id==user_id
    ).first()
    if report is None:
        return None

    old = db.query(Application).filter(
        Application.report_id==report_id
    ).first()
    if old is not None:
        return old

    row = Application(user_id=user_id,report_id=report_id)
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
    except SQLAlchemyError:
        db.rollback()
        raise
    return row


def list_apply(db:Session,user_id:int):
    return db.query(
        Application.id,Application.user_id,Application.report_id,
        Application.status,Application.note,
        Application.created_at,Application.updated_at,
        SavedReport.title.label('title'),
        SavedReport.company.label('company')
    ).join(
        SavedReport,Application.report_id == SavedReport.id
    ).filter(
        Application.user_id==user_id
    ).order_by(Application.updated_at.desc()).all()

def update_apply(db:Session,user_id:int,apply_id:int,data:ApplyUpdate):
    row=db.query(Application).filter(
        Application.id==apply_id,Application.user_id==user_id
    ).first()
    if row is None:
        return row
    try:
        row.status,row.note=data.status,data.note
        db.commit()
        db.refresh(row)
    # refresh() 的具体实现；知道它用于读取数据库中的最新值即可。
    except SQLAlchemyError:
        db.rollback()
        raise
    return row