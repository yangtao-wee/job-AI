from passlib.context import CryptContext
# 导入密码处理工具。

from ..config import settings
from jose import jwt
from datetime import datetime,timedelta,timezone

pwd_context=CryptContext(
    schemes=['bcrypt'],
    deprecated='auto'
)
# 创建密码处理器。告诉它：我们使用：bcrypt算法。

def hash_password(password):
    return pwd_context.hash(password)
# 加密函数

# 验证密码
def verify_password(
        piain_password,
        hashed_password
):
    return pwd_context.verify(
        piain_password,
        hashed_password
    )




# 生成登录凭证
def create_access_token(data):

    # 复制数据：
    to_encode =  data.copy()

    # 设置过期时间：
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    to_encode.update(
        {
            'exp':expire
        }
    )

    # 把数据变成字符串。
    token = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    return token

def decode_access_token(token):
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm]
    )
    return payload