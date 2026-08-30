from fastapi import APIRouter,Depends
# Depends：让FastAPI自动执行依赖函数。
from ..dependencies import get_current_user
# 【自己项目定义】验证JWT并取得当前用户。
from ..models import User
from ..schemas import RagAsk,RagAnswer
from ..services.rag_service import answer_question
from ..services.kb_service import load_parts

router=APIRouter()

@router.post('/ask',response_model=RagAnswer)
# response_model它要求接口最终响应必须符合RagAnswer结构，也会把响应格式展示在FastAPI接口文档中
def ask(data:RagAsk,_user:User=Depends(get_current_user)):
# _user前面的下划线表示：
# 这个用户对象当前只用于证明已经登录，函数内部暂时不读取它。
    return answer_question(data.question,load_parts())