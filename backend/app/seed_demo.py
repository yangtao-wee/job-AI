import json
import shutil
from datetime import datetime
from pathlib import Path

from .database import SessionLocal
from .models import User, JobLead, Resume, ResumeAnalysis, SavedReport
from .utils.security import hash_password

DEMO_USER = 'demo'
DEMO_PASSWORD = 'demo2026'
DEMO_EMAIL = 'demo@example.com'
DATA_DIR = Path(__file__).resolve().parent / 'demo_data'
UPLOAD_DIR = Path(__file__).resolve().parents[1] / 'uploads' / 'resumes'

def seed_leads(db, user_id):
    rows = json.loads((DATA_DIR / 'leads.json').read_text(encoding='utf-8'))
    have = {
        lead.url
        for lead in db.query(JobLead).filter(JobLead.user_id == user_id)
    }
    added = 0
    for data in rows:
        if data['url'] in have:
            continue
        db.add(JobLead(user_id=user_id, **data))
        added += 1
    db.commit()
    return added

def get_demo_user(db):
    user = db.query(User).filter(User.username == DEMO_USER).first()
    if user is not None:
        return user
    user = User(
        username=DEMO_USER,
        email=DEMO_EMAIL,
        password=hash_password(DEMO_PASSWORD),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def seed_resume(db, user_id):
    resume = db.query(Resume).filter(Resume.user_id == user_id).first()
    if resume is not None:
        return resume
    data = json.loads((DATA_DIR / 'profile.json').read_text(encoding='utf-8'))
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dst = UPLOAD_DIR / f'{user_id}_demo.pdf'
    shutil.copyfile(DATA_DIR / 'demo_resume.pdf', dst)
    resume = Resume(user_id=user_id, stored_filename=dst.name, **data['resume'])
    db.add(resume)
    db.flush()
    db.add(ResumeAnalysis(resume_id=resume.id, **data['analysis']))
    db.commit()
    db.refresh(resume)
    return resume

def seed_reports(db, user_id, resume_id):
    have = db.query(SavedReport).filter(SavedReport.user_id == user_id).first()
    if have is not None:
        return 0
    data = json.loads((DATA_DIR / 'profile.json').read_text(encoding='utf-8'))
    leads = {
        lead.url: lead
        for lead in db.query(JobLead).filter(JobLead.user_id == user_id)
    }
    added = 0
    for item in data['reports']:
        lead = leads.get(item['lead_url'])
        if lead is None:
            continue
        report = SavedReport(user_id=user_id, resume_id=resume_id, **item['report'])
        db.add(report)
        db.flush()
        lead.report_id = report.id
        lead.deep_at = datetime.now()
        for name, value in item['deep'].items():
            setattr(lead, name, value)
        added += 1
    db.commit()
    return added


def seed_demo():
    db = SessionLocal()
    try:
        user = get_demo_user(db)
        added = seed_leads(db, user.id)
        resume = seed_resume(db, user.id)
        reports = seed_reports(db, user.id, resume.id)
        print(f'演示账号 {DEMO_USER}(id={user.id})，'
              f'新增岗位 {added} 条，报告 {reports} 份')
    finally:
        db.close()


if __name__ == '__main__':
    seed_demo()