from fastapi import APIRouter,Depends
from ..dependencies import get_current_user
from ..models import User
from ..schemas import AgentAnswer,AgentAsk
from ..services.agent_service import ask_agent

router=APIRouter()

@router.post('/ask',response_model=AgentAnswer)
# response_model：【框架提供】要求返回结果符合 AgentAnswer
def ask(data:AgentAsk,_user:User=Depends(get_current_user)):
    return AgentAnswer(answer=ask_agent(data.goal))