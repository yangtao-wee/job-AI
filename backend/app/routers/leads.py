from fastapi import APIRouter,Depends,Query,HTTPException
from sqlalchemy.orm import Session
import logging
from ..dependencies import get_current_user,get_db,check_limit
from ..models import User
from ..schemas import LeadBatch,LeadOut,LeadSaveResult,LeadJdBatch,LeadJdResult,LeadAnalyzeRequest,LeadAnalyzeResult,LeadStatusUpdate,LeadSkipRequest,LeadSkipResult
from ..services.lead_service import save_leads,list_leads,save_jd,load_proofs,analyze_next,update_status,skip_below
from ..services.cache_service import take_lock, free_lock

log=logging.getLogger(__name__)
router=APIRouter()


@router.post('/batch',response_model=LeadSaveResult)
def upload_leads(
    request:LeadBatch,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    return save_leads(db,current_user.id,request.leads)


@router.get('',response_model=list[LeadOut])
def my_leads(
    status:str|None=Query(None),
    offset:int=Query(0,ge=0),
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    return list_leads(db,current_user.id,status,offset)

@router.post('/jd',response_model=LeadJdResult)
def upload_jd(
    request:LeadJdBatch,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    return save_jd(db,current_user.id,request.items)

@router.post('/analyze',response_model=LeadAnalyzeResult)
def analyze_lead(
    request:LeadAnalyzeRequest,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    check_limit('lead', current_user.id, 30, 3600)
    try:
        proofs=load_proofs(db,current_user.id,request.resume_id)
    except ValueError as error:
        raise HTTPException(status_code=404,detail=str(error)) from error
    lock=take_lock(f'lead:analyze:{current_user.id}')
    if lock is None:
        log.warning(
            'lead_analysis_lock_unavailable user_id=%s resume_id=%s',
            current_user.id,request.resume_id
        )
        raise HTTPException(status_code=503,detail='精判任务繁忙，请稍后重试')
    try:
        return analyze_next(db,current_user.id,request.resume_id,proofs,request.min_score)
    except Exception as error:
        log.exception(
            'lead_analysis_failed user_id=%s resume_id=%s',
            current_user.id,request.resume_id
        )
        raise HTTPException(status_code=502,detail='精判失败，请稍后重试') from error
    finally:
        free_lock(lock)


@router.patch('/{lead_id}',response_model=LeadOut)
def update_lead(
    lead_id:int,
    request:LeadStatusUpdate,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    row=update_status(db,current_user.id,lead_id,request.status)
    if row is None:
        raise HTTPException(status_code=404,detail='岗位不存在')
    return row


@router.post('/skip-below',response_model=LeadSkipResult)
def skip_low_score(
    request:LeadSkipRequest,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    return {'skipped':skip_below(db,current_user.id,request.below)}
