from fastapi import APIRouter,Depends
from ..dependencies import get_current_user,check_limit
from ..models import User
from ..schemas import AgentAnswer,AgentAsk
from ..services.agent_service import ask_agent

router=APIRouter()

@router.post('/ask',response_model=AgentAnswer)
# response_model：【框架提供】要求返回结果符合 AgentAnswer
def ask(data:AgentAsk,current_user:User=Depends(get_current_user)):
    check_limit('agent', current_user.id, 30, 3600)
    history=[item.model_dump() for item in data.history]
    return AgentAnswer(
        answer=ask_agent(data.goal,history)
    )
