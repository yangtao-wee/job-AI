from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func,Text,JSON
# 我们需要告诉数据库：字段是什么类型。

from .database import Base
# 导入：Base class Job(Base):
# 需要继承它。
# 告诉SQLAlchemy：
# 这个类不是普通Python类。
# 它是一张数据库表。

# class Job(Base):创建数据库模型。
# SQLAlchemy看到：
# “哦，这是一个表。”
class Job(Base):

#     # 这个Python类对应数据库里面：
#     如果没有：
# SQLAlchemy不知道：
# 这个类叫什么表。
    __tablename__='jobs'

# id字段
# Column
# 代表：
# 数据库的一列。
# 例如：
# 表：id就是一列。
# Integer
# 类型：
# 数字。
    
    id=Column(
        Integer,
        primary_key=True,
        index=True
    )
# primary_key=True
# 主键。
# 什么意思？
# 每条数据必须有唯一编号。
# # 例如：id

# 1 Python工程师

# 2 Vue工程师

# 3 AI产品经理

# index=True
# 创建索引。
# 先简单理解：
# 提高查询速度。

    title = Column(
        String
    )

    company = Column(
        String
    )

    salary = Column(
        String
    )

    location = Column(
        String
    )

    skills= Column(
        String
    )   

    description = Column(Text , nullable=False,default='')
# nullable=False：【项目规则】，不允许数据库存入空值NULL。
# default=''：【项目规则】，没有内容时暂时使用空字符串。
class User(Base):
    __tablename__='users'
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )


    username = Column(
        String,
        unique=True
    )
# unique是否必须唯一

    email = Column(
        String,
        unique=True
    )


    password = Column(
        String
    )

class Resume(Base):
    __tablename__ = 'resumes'

    id = Column(Integer,primary_key=True,index=True)
    user_id  = Column(Integer,ForeignKey('users.id'),
nullable=False,index=True)
    original_filename = Column(String,nullable=False)
    stored_filename = Column(String,unique=True,nullable=False)
    content_type = Column(String,nullable=False)
    file_size = Column(Integer,nullable=False)
    created_at = Column(DateTime,server_default=func.now(),nullable=False)


# ORM模型增加字段
class ResumeAnalysis(Base):
    __tablename__ = 'resume_analyses'
    id = Column(Integer,primary_key=True,index=True)
    resume_id = Column(
        Integer,
        ForeignKey('resumes.id'),
        unique=True,
        nullable=False,
        index=True
    )
    summary = Column(Text,nullable=False)
    skills = Column(JSON,nullable=False)
    work_experience = Column(JSON,nullable=False,default=list)
    strengths = Column(JSON,nullable=False)
    improvement_suggestions = Column(JSON,nullable=False)
    recommended_positions = Column(JSON,nullable=False)
    created_at = Column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )


class SavedReport(Base):
    __tablename__='saved_reports'

    id = Column(Integer,primary_key=True)
    user_id = Column(Integer,ForeignKey('users.id'),nullable=False,index=True)
    # index=True为用户编号建立索引，方便按用户查询历史。
    resume_id=Column(Integer,ForeignKey('resumes.id'),nullable=False)
    title = Column(String(200),nullable=False)
    company = Column(String(200),nullable=False)
    # nullable=False不允许数据库中的空值 NULL；不等于禁止空字符串。
    jd = Column(Text,nullable=False)
    content = Column(JSON,nullable=False)
    created_at = Column(DateTime,server_default=func.now(),nullable=False)

