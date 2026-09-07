from fastapi import APIRouter,Depends,Query
from sqlalchemy.orm import Session

from ..dependencies import get_current_user,get_db
from ..models import User
from ..schemas import LeadBatch,LeadOut,LeadSaveResult
from ..services.lead_service import save_leads,list_leads

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