from ..models import User
from ..utils.security import hash_password

def create_user(db,user):
    new_user =User(
        username = user.username,
        email=user.email,
        password=hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
# 刷新对象

    return new_user