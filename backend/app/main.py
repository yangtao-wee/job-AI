# 从 fastapi 这个第三方库中导入 FastAPI 类。
# 你可以先把“类”理解成创建某类对象的模板。
# 下面我们会使用这个模板，创建整个后端应用。
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from .schemas import JobSchema
from .database import engine
from .routers import jobs,users,resumes,rag
# engine
# 知道：
# 数据库在哪里。

# 拿模型集合。
# 因为：
# Base里面知道：
# 有哪些表。
from .models import Base

Base.metadata.create_all(bind=engine)
# FastAPI启动时：根据我定义好的模型，去数据库创建对应的表
# 检查数据库。
# 如果没有表：
# 创建。
# 如果已经有：
# 不重复创建。
app = FastAPI()

#include_router把一个路由模块加入这个应用。 jobs.py里面的router对象 
# include_router把用户部门登记到 FastAPI 总公司。
app.include_router(jobs.router)

app.include_router(
    users.router,
    # prefix给所有用户接口统一增加 /users 前缀。
    prefix='/users',
    # tags=["users"]：让接口文档把它归入用户分类。
    tags=['users']
    )

app.include_router(
    resumes.router,
    prefix='/resumes',
    tags=['resumes']
)

app.include_router(
    rag.router,
    prefix='/rag',
    tags=['rag']
)

app.add_middleware(
    CORSMiddleware,
    # 保安
    allow_origins=[
        # 允许哪些前端地址。
        'http://localhost:5174',
        'http://localhost:5173'
    ],
    allow_methods=['*'],
    # 允许所有HTTP方法：比如：GET POST PUT DELETE
    allow_headers=['*'],
    # 允许请求头。
)

# @app.get('/health') 叫作“装饰器”。
# 它的作用是告诉 FastAPI：
# 当客户端使用 GET 请求访问 /health 地址时，执行下面的 health 函数。
#
# GET 是一种 HTTP 请求方法，通常用来读取数据，而不是修改数据。
# /health 是接口路径，这个接口常用来检查后端服务是否正常运行。
@app.get('/health')
def health():
    # return 表示把结果返回给请求这个接口的客户端。
    # 这里返回的是一个 Python 字典，包含一组“键和值”。
    # FastAPI 会自动把这个字典转换成 JSON 响应。
    return {
        # status 是字段名，ok 表示服务目前运行正常。
        'status': 'ok'
    }

# response_model告诉FastAPI：这个接口返回的数据格式是什么。

    
    
