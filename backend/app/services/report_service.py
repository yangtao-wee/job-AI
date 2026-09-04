from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from ..models import SavedReport
from ..schemas import JobAssistRequest, Report

def save_report(db: Session, user_id: int, request: JobAssistRequest, result: Report) -> None:
    row = SavedReport(
        user_id=user_id, resume_id=request.resume_id,
        title=request.job_title, company=request.company,
        jd=request.jd_text, content=result.model_dump(mode='json')
    )
    try:
        db.add(row)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

def list_reports(db:Session,user_id:int,offset:int=0):
    return(
        db.query(SavedReport.id,SavedReport.title,SavedReport.company,
        SavedReport.created_at).filter(
            SavedReport.user_id==user_id
        ).order_by(
            # 编号从大到小排列，最新保存的在前面。
            SavedReport.id.desc()
        ).offset(offset).limit(20).all()
    # 跳过指定数量，再最多取20条。后续页面可以加载下一批。
    # .all()：得到记录列表；没有记录就返回空列表。
    )

def get_report(db:Session,user_id,report_id:int):
    return db.query(SavedReport).filter(
        SavedReport.id == report_id,
        SavedReport.user_id==user_id
    ).first()