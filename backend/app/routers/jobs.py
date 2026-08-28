from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy.orm  import Session

from ..database import SessionLocal
from ..dependencies import get_current_user,get_db
from ..models import Job,User
from ..schemas import JobMatchRequest,JobMatchResponse,JobRequirementResult,SemMatch
from ..services.matching_service import calculate_skill_score,get_user_resume_analysis,calculate_keyword_score,calculate_required_skill_score,merge_job_skills,calculate_experience_score,score_role,score_pref
from ..services.job_service import get_all_jobs
from ..services.ai_job_service import analyze_job_with_ai
from ..services.semantic_service import calc_sim,MODEL
from ..services.ai_match_service import explain

router = APIRouter()

@router.get('/jobs')
def get_jobs():
    db = SessionLocal()
    jobs = get_all_jobs(db)
    db.close()
    return jobs

@router.post('/jobs/match',response_model=JobMatchResponse)

def match_job(
    request:JobMatchRequest,
    current_user:User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    analysis = get_user_resume_analysis(db,request.resume_id,current_user.id)
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not analysis or not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='简历分析或岗位不存在'
        )
    job_requirements = analyze_job_with_ai(job.description)
    merged_job_skills = merge_job_skills(
         job.skills,job_requirements.required_skills
    )
    skill_match = calculate_skill_score(analysis.skills,merged_job_skills)
    keyword_match = calculate_keyword_score(analysis.skills,job.description)
    required_skill_match = calculate_required_skill_score(analysis.skills,job_requirements.required_skills)
    exp_match=calculate_experience_score(
         analysis.work_experience,
         job_requirements.responsibilities
    )
    role = score_role(job.title,analysis.recommended_positions)
    pref = score_pref(job.location,job.salary,request.city,request.min_pay)
    r_text=' '.join([analysis.summary or '',*analysis.skills,*analysis.work_experience])
    # or ''：如果数据为空，就使用空文字，避免拼接报错。
    # *analysis.skills：把技能列表中的每一项展开。
    # round(sim,3)：保留3位小数。
    j_text=' '.join([job.title or '',job.skills or '',job.description or ''])
    sim = calc_sim(r_text,j_text)
    sem = SemMatch(sim=round(sim,3),model=MODEL,note='语义相似度,仅作参考')
    total=skill_match.score + keyword_match.score + exp_match.score +role.score + pref.score
    reasons=skill_match.matched_skills+[hit.resume_evidence for hit in exp_match.matches]
    gaps=skill_match.missing_skills+required_skill_match.missing_skills
    ai_note=explain(total,sem.sim,reasons,gaps)
    return JobMatchResponse(
        resume_id=request.resume_id,
        job_id=request.job_id,
        current_score=total,
        current_max_score=100,
        skill_match=skill_match,
        keyword_match=keyword_match,
        required_skill_match=required_skill_match,
        experience_match=exp_match,
        role_match=role,
        pref_match=pref,
        sem_match=sem,
        ai_explain=ai_note
    )

@router.post('/jobs/{job_id}/analysis',
             response_model=JobRequirementResult)
# response_model：【框架提供】，检查返回结果必须符 
def analyze_job(
    job_id:int,
    _current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
            raise HTTPException(status_code=404,detail='岗位不存在')
    return analyze_job_with_ai(job.description)

