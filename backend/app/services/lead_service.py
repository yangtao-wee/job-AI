from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pathlib import Path
from datetime import datetime

from .job_assist_service import make_report
from .report_service import save_report
from ..models import JobLead,Resume
from ..services.resume_parser import extract_pdf_text
from ..schemas import LeadIn,LeadJdIn,JobAssistRequest


def save_leads(db:Session,user_id:int,leads:list[LeadIn])->dict:
    uniq={lead.url:lead for lead in leads}
    rows={
        row.url:row
        for row in db.query(JobLead).filter(
            JobLead.user_id==user_id,
            JobLead.url.in_(uniq.keys())
        )
    }
    added=0
    updated=0
    for url,lead in uniq.items():
        row=rows.get(url)
        if row is None:
            db.add(JobLead(user_id=user_id,**lead.model_dump()))
            added+=1
        elif row.quick_score!=lead.quick_score:
            row.quick_score=lead.quick_score
            updated+=1
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return {'added':added,'updated':updated,'total':len(uniq)}


def list_leads(db:Session,user_id:int,status:str|None=None,
               offset:int=0,limit:int=50)->tuple[list[JobLead],int]:
    q=db.query(JobLead).filter(JobLead.user_id==user_id)
    if status:
        q=q.filter(JobLead.status==status)
    total=q.count()
    rows=(
        q.order_by(JobLead.quick_score.desc(),JobLead.id.desc())
        .offset(offset).limit(limit).all()
    )
    return rows,total

def save_jd(db:Session,user_id:int,items:list[LeadJdIn])->dict:
    uniq={item.url:item for item in items}
    rows=db.query(JobLead).filter(
        JobLead.user_id==user_id,
        JobLead.url.in_(uniq.keys())
    ).all()
    updated=0
    for row in rows:
        item=uniq[row.url]
        if row.jd_text==item.jd_text:
            continue
        row.jd_text=item.jd_text
        row.deep_at=None
        row.deep_ok=0
        row.deep_part=0
        row.deep_total=0
        row.report_id=None
        updated+=1
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return {'updated':updated,'missed':len(uniq)-len(rows)}


def load_proofs(db:Session,user_id:int,resume_id:int)->list[str]:
    resume=db.query(Resume).filter(
        Resume.id==resume_id,
        Resume.user_id==user_id
    ).first()
    if resume is None:
        raise ValueError('简历不存在')
    if resume.content_type!='application/pdf':
        raise ValueError('当前仅支持PDF简历')
    path=Path(__file__).resolve().parents[2]/'uploads'/'resumes'/resume.stored_filename
    return [line.strip() for line in extract_pdf_text(path).splitlines() if line.strip()]

def analyze_next(db:Session,user_id:int,resume_id:int,proofs:list[str],min_score:int=60)->dict:
    base=db.query(JobLead).filter(
        JobLead.user_id==user_id,
        JobLead.jd_text.isnot(None),
        JobLead.deep_at.is_(None),
        JobLead.quick_score>=min_score,
        JobLead.status!='已跳过'
    )
    lead=base.order_by(JobLead.quick_score.desc()).first()
    if lead is None:
        return {'analyzed':False,'remaining':0}
    result=make_report(lead.jd_text,proofs)
    row=save_report(db,user_id,JobAssistRequest(
        resume_id=resume_id,
        jd_text=lead.jd_text,
        job_title=lead.title[:100],
        company=(lead.company or '未知')[:100]
    ),result,commit=False)
    lead.deep_ok=sum(1 for c in result.checks if c.status=='有依据')
    lead.deep_part=sum(1 for c in result.checks if c.status=='部分支持')
    lead.deep_total=len(result.checks)
    lead.report_id=row.id
    lead.deep_at=datetime.now()
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return {
        'analyzed':True,
        'remaining':base.count(),
        'lead_id':lead.id,
        'title':lead.title,
        'deep_ok':lead.deep_ok,
        'deep_part':lead.deep_part,
        'deep_total':lead.deep_total
    }


def update_status(db:Session,user_id:int,lead_id:int,status:str):
    lead=db.query(JobLead).filter(
        JobLead.id==lead_id,
        JobLead.user_id==user_id
    ).first()
    if lead is None:
        return None
    lead.status=status
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(lead)
    return lead


def skip_below(db:Session,user_id:int,below:int)->int:
    n=db.query(JobLead).filter(
        JobLead.user_id==user_id,
        JobLead.quick_score<below,
        JobLead.status.in_(['新抓取','待投递'])
    ).update({'status':'已跳过'},synchronize_session=False)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return n

def mark_above(db:Session,user_id:int,above:int)->int:
    n=db.query(JobLead).filter(
        JobLead.user_id==user_id,
        JobLead.quick_score>=above,
        JobLead.status.in_(['新抓取','已跳过'])
    ).update({'status':'待投递'},synchronize_session=False)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return n

def unmark_all(db:Session,user_id:int)->int:
    n=db.query(JobLead).filter(
        JobLead.user_id==user_id,
        JobLead.status=='待投递'
    ).update({'status':'新抓取'},synchronize_session=False)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return n