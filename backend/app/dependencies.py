from fastapi import Depends,HTTPException,status
from fastapi.security import HTTPAuthorizationCredentials,HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from .models import User
from .utils.security import decode_access_token
from .database import SessionLocal

# Depends：让 FastAPI 自动提供 Token 和数据库连接。
# HTTPException、status：返回标准 401错误。
# HTTPBearer：从请求头读取 Bearer Token。
# HTTPAuthorizationCredentials：表示读取到的身份数据。
# JWTError：捕获 Token 被修改或过期等错误。
# Session：标明数据库连接类型。
# User：查询用户表。
# decode_access_token：验证并解码 Token。
bearer_scheme = HTTPBearer()
# 它像公司门口的门禁读取器，负责从下面的请求头取出门禁卡：
def get_db():
    db=SessionLocal()
    try:
        yield db
        # yield db：。把东西借出去，等别人用完还会回来继续执行清理。
    finally:
        db.close()
        # finally：无论成功、报错还是提前返回，都关闭窗口。

def get_current_user(
        credentials:HTTPAuthorizationCredentials=
        Depends(bearer_scheme),
        db:Session = Depends(get_db)
):
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get('user_id')
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='TOKEN无效或已过期'
        )
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='用户不存在'
        )
    return user