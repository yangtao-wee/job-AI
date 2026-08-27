from fastapi import APIRouter,Depends,HTTPException,status
from ..schemas import UserCreate,UserResponse,UserLogin
from ..services.user_service import create_user
from ..models import User
from ..utils.security import verify_password,create_access_token
from sqlalchemy import or_
from sqlalchemy.orm import Session
from ..dependencies import get_db,get_current_user
router = APIRouter()

@router.post('/register',response_model=UserResponse,
             status_code=status.HTTP_201_CREATED)

# UserCreate代表：接收前端用户提交的数据。
def registerr(user:UserCreate,
    db:Session=Depends(get_db)):
    existing_user=db.query(User).filter(
        or_(User.username==user.username,
            User.email==user.email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='用户名或邮箱已存在'
        )
    result = create_user(db,user)
    return result

@router.post('/login')
def login(login_data:UserLogin,
          db:Session=Depends(get_db)):
    db_user = db.query(User).filter(
        User.username==login_data.username
    ).first()
    if not db_user or not verify_password(
        login_data.password,
        db_user.password
    ):
# if not db_user or...：用户不存在或者密码错误，都算登录失败。
# or具有短路功能：如果用户不存在，就不会继续读取其密码，避免程序报错。
# login_data.password：用户刚输入的明文密码。
# db_user.password：数据库保存的加密密码。
# raise HTTPException：立即停止登录流程，像保安拒绝放行。
# HTTP_401_UNAUTHORIZED：表示身份验证失败。
# # detail：返回给前端的错误说明。
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='用户名或密码错误'
        )

    token = create_access_token(
        {
            'user_id':db_user.id
        }
    )

    return{
        'access_token':token
    }

@router.get('/me',response_model=UserResponse)
def get_me(
    current_user:User = Depends(get_current_user)
):
    return current_user