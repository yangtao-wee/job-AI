from .database import SessionLocal,engine
from .models import Job,Base
# Job是什么？不是数据库。它是：Python里面代表岗位表的模型。

Base.metadata.create_all(bind=engine)

# 打开数据库操作窗口。
db=SessionLocal()
# db是打开数据库后的“管理员账号”。

jobs = [
      Job(
        title="Python开发工程师",
        company="深圳AI科技公司",
        salary="15-20K",
        location="深圳",
        skills="Python,FastAPI,AI"
    ),


    Job(
        title="Vue前端工程师",
        company="互联网公司",
        salary="12-18K",
        location="广州",
        skills="Vue,JavaScript,CSS"
    ),


    Job(
        title="AI产品经理",
        company="人工智能公司",
        salary="20-30K",
        location="上海",
        skills="AI,产品设计,大模型"
    )
]

# 把这些数据放进去。
db.add_all(jobs)

# commit：提交。没有它：数据可能不会永久保存。
db.commit()

# 释放连接。养成习惯：
db.close()