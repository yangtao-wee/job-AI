from fastapi import APIRouter,Depends,Query,HTTPException
from sqlalchemy.orm import Session
import logging
from ..config import settings
from ..dependencies import get_current_user,get_db,check_limit
from ..models import User
from ..schemas import LeadBatch,LeadOut,LeadSaveResult,LeadJdBatch,LeadJdResult,LeadAnalyzeRequest,LeadAnalyzeResult,LeadStatusUpdate,LeadSkipRequest,LeadSkipResult,LeadMarkRequest,LeadMarkResult,LeadUnmarkResult,LeadPage,LeadStats,LeadDeleteRequest,LeadDeleteResult,LeadRescoreRequest,LeadRescoreResult,LeadReadList
from ..services.lead_service import save_leads,list_leads,save_jd,load_proofs,analyze_next,update_status,skip_below,mark_above,unmark_all,lead_stats,delete_lead,delete_unapplied,delete_without_jd,score_context,rescore_all,list_unread_jd
from ..services.cache_service import take_lock, free_lock

log=logging.getLogger(__name__)
router=APIRouter()


@router.post('/batch',response_model=LeadSaveResult)
def upload_leads(
    request:LeadBatch,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    # 带了简历编号就按求职方案重新打分（含工资）；没带就只存插件给的标题分
    ctx=score_context(db,current_user,request.resume_id) if request.resume_id else None
    return save_leads(db,current_user.id,request.leads,ctx)


@router.get('',response_model=LeadPage)
def my_leads(
    status:str|None=Query(None),
    offset:int=Query(0,ge=0),
    limit:int|None=Query(None,ge=1,le=200),
    min_score:int=Query(0,ge=0,le=100),
    order:str=Query('分数高'),
    q:str=Query('',max_length=50),
    kind:str=Query('',max_length=20),
    tier:str=Query('',max_length=20),
    in_jd:bool=Query(False),
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    size=limit or settings.lead_page_size
    rows,total,facets=list_leads(db,current_user.id,status,offset,size,min_score,order,q,kind,tier,in_jd)
    return {'items':rows,'total':total,'offset':offset,'limit':size,**facets}

@router.get('/stats',response_model=LeadStats)
def read_stats(
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    return lead_stats(db,current_user.id)


@router.get('/unread-jd',response_model=LeadReadList)
def unread_jd_leads(
    limit:int=Query(50,ge=1,le=500),
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    # 岗位池「补读JD」按钮：把要读的岗位交给插件，插件挨个打开详情页读
    return list_unread_jd(db,current_user.id,limit)


@router.post('/jd',response_model=LeadJdResult)
def upload_jd(
    request:LeadJdBatch,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    # 读不到简历或简历分析，就只保存 JD，不打分
    ctx=score_context(db,current_user,request.resume_id) if request.resume_id else None
    return save_jd(db,current_user.id,request.items,ctx)


@router.post('/rescore',response_model=LeadRescoreResult)
def rescore_leads(
    request:LeadRescoreRequest,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    check_limit('lead_rescore', current_user.id, 20, 3600)
    ctx=score_context(db,current_user,request.resume_id)
    if ctx is None:
        raise HTTPException(status_code=404,detail='简历或简历分析不存在，请先上传简历并做 AI 分析')
    return rescore_all(db,current_user.id,ctx)

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


@router.delete('/{lead_id}')
def remove_lead(
    lead_id:int,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    result=delete_lead(db,current_user.id,lead_id)
    if result=='不存在':
        raise HTTPException(status_code=404,detail='岗位不存在')
    if result=='已投递':
        raise HTTPException(status_code=409,detail='已投递的岗位不能删除，请先改成其他状态')
    return {'deleted':lead_id}

@router.post('/skip-below',response_model=LeadSkipResult)
def skip_low_score(
    request:LeadSkipRequest,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    return {'skipped':skip_below(db,current_user.id,request.below)}

@router.post('/delete-unapplied',response_model=LeadDeleteResult)
def delete_unapplied_leads(
    request:LeadDeleteRequest,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    return {'deleted':delete_unapplied(db,current_user.id,request.status)}


@router.post('/delete-without-jd',response_model=LeadDeleteResult)
def delete_leads_without_jd(
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    return {'deleted':delete_without_jd(db,current_user.id)}

@router.post('/mark-above',response_model=LeadMarkResult)
def mark_high_score(
    request:LeadMarkRequest,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    return {'marked':mark_above(db,current_user.id,request.above)}


@router.post('/unmark',response_model=LeadUnmarkResult)
def unmark_all_leads(
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    return {'unmarked':unmark_all(db,current_user.id)}
