from ..models import Job
def get_all_jobs(db):
    jobs = db.query(Job).all()
    return jobs