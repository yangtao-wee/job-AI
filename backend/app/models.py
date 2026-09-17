from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func,Text,JSON,UniqueConstraint
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

    title = Column(String(200))
    company = Column(String(200))
    salary = Column(String(50))
    location = Column(String(100))
    skills = Column(String(500))

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
        String(50),
        unique=True
    )
# unique是否必须唯一

    email = Column(
        String(255),
        unique=True
    )


    password = Column(
        String(255)
    )
    token_version = Column(Integer, nullable=False, server_default='0')
    # 求职方案：[{name, positions, junior, max_years, good_words}]，岗位按每套方案打分、取最高
    job_targets = Column(JSON, nullable=True)
class Resume(Base):
    __tablename__ = 'resumes'

    id = Column(Integer,primary_key=True,index=True)
    user_id  = Column(Integer,ForeignKey('users.id'),
nullable=False,index=True)
    original_filename = Column(String(255),nullable=False)
    stored_filename = Column(String(255),unique=True,nullable=False)
    content_type = Column(String(100),nullable=False)
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
    projects = Column(JSON, nullable=False, default=list)
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


class Application(Base):
    __tablename__ = 'applications'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    report_id = Column(Integer, ForeignKey('saved_reports.id'), nullable=False, unique=True)
    status = Column(String(20), nullable=False, default='待投递')
    note = Column(Text, nullable=False, default='')
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class JobLead(Base):
    __tablename__ = 'job_leads'
    __table_args__ = (
        UniqueConstraint('user_id', 'url', name='uq_lead_user_url'),
    )
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    company = Column(String(200), nullable=False, default='')
    url = Column(String(500), nullable=False)
    tags = Column(JSON, nullable=False, default=list)
    quick_score = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default='新抓取')
    jd_text = Column(Text, nullable=True)
    deep_ok = Column(Integer, nullable=False, server_default='0')
    deep_part = Column(Integer, nullable=False, server_default='0')
    deep_total = Column(Integer, nullable=False, server_default='0')
    report_id = Column(Integer, ForeignKey('saved_reports.id', name='fk_lead_report'), nullable=True)
    deep_at = Column(DateTime, nullable=True)
    # 原始分（只看标题和标签）；空着表示和 quick_score 一样
    base_score = Column(Integer, nullable=True)
    # JD 命中的门槛，比如 ['要全日制本科']
    jd_flags = Column(JSON, nullable=True)
    # JD 命中的能力项，比如 ['Python', 'API/接口']；用于解释粗筛分数。
    jd_hits = Column(JSON, nullable=True)
    # 岗位池上显示的合适 / 不合适的点，比如 ['方向对上：亚马逊运营助理', 'HR刚刚活跃']、['要外语/粤语（最高50）']
    pros = Column(JSON, nullable=True)
    cons = Column(JSON, nullable=True)
    # JD 扣了几分
    jd_cut = Column(Integer, nullable=False, server_default='0')
    # 分数来自哪套求职方案，比如「简历A」
    target = Column(String(20), nullable=True)
    # 列表页的工资原文，比如「8-13K·14薪」（数字可能是 BOSS 的特殊字体字符）
    salary = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    @property
    def has_jd(self):
        return bool((self.jd_text or '').strip())
