from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ..models import JobLead
from ..schemas import LeadIn


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


def list_leads(db:Session,user_id:int,status:str|None=None,offset:int=0)->list[JobLead]:
    q=db.query(JobLead).filter(JobLead.user_id==user_id)
    if status:
        q=q.filter(JobLead.status==status)
    return (
        q.order_by(JobLead.quick_score.desc(),JobLead.id.desc())
        .offset(offset).limit(50).all()
    )