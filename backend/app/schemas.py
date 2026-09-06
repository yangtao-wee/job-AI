from pydantic import BaseModel,ConfigDict,Field
from datetime import datetime
from typing import Literal
# BaseModel：Pydantic提供的数据模型基类，负责检查和转换数据。
# ConfigDict：Pydantic提供的模型配置工具，负责设置整个类的验证规则。
# Field：Pydantic提供的字段配置工具，负责设置长度、范围等验证条件。
# datetime：Python标准库提供的日期时间类型。


# 岗位返回结构：规定后端向前端返回一条岗位时包含哪些数据。
class JobSchema(BaseModel):
    id:int  # 岗位编号。
    title:str  # 岗位名称。
    company:str  # 公司名称。
    salary:str  # 薪资范围。
    location:str  # 工作地点。
    skills:str  # 岗位需要的技能文字。
    description:str  # 完整岗位描述。
    # 允许从数据库对象的同名属性读取以上字段。
    model_config=ConfigDict(from_attributes=True)


# 用户注册请求：规定前端注册时必须提交的数据。
class UserCreate(BaseModel):
    username:str  # 用户名。
    email:str  # 电子邮箱。
    password:str  # 未加密的原始密码，只用于接收请求，不能直接保存到数据库。


# 用户信息返回结构：只返回可以公开给前端的用户信息，不返回密码。
class UserResponse(BaseModel):
    id:int  # 用户编号。
    username:str  # 用户名。
    email:str  # 电子邮箱。
    # 允许从数据库用户对象中读取字段。
    model_config=ConfigDict(from_attributes=True)


# 用户登录请求：规定登录时需要提交用户名和密码。
class UserLogin(BaseModel):
    username:str  # 用户名。
    password:str  # 用户输入的原始密码，用于和密码摘要进行验证。


# 简历上传结果：规定上传成功后返回的文件信息。
class ResumeResponse(BaseModel):
    id:int  # 简历编号。
    original_filename:str  # 用户上传时的原始文件名。
    content_type:str  # 文件类型，例如PDF。
    file_size:int  # 文件大小，单位是字节。
    created_at:datetime  # 简历上传时间。
    # 允许从数据库简历对象中读取字段。
    model_config=ConfigDict(from_attributes=True)


# 模型生成的简历分析结构：限制大模型必须返回哪些内容。
class ResumeAIAnalysis(BaseModel):
    resume_id:int  # 被分析的简历编号，最终应由后端可信数据覆盖。
    summary:str  # 简历总体总结。
    skills:list[str]  # 从简历中识别出的技能列表。
    work_experience:list[str]  # 从简历中识别出的工作或项目经历。
    strengths:list[str]  # 候选人的优势列表。
    improvement_suggestions:list[str]  # 简历改进建议列表。
    recommended_positions:list[str]  # 推荐岗位列表。
    ai_ok:bool=True  # 模型是否正常完成分析，默认正常。


# 简历分析接口返回结构：在模型分析内容上补充数据库记录信息。
class ResumeAnalysisResponse(ResumeAIAnalysis):
    id:int  # 简历分析记录编号。
    created_at:datetime  # 分析结果创建时间。
    # 允许从数据库简历分析对象中读取字段。
    model_config=ConfigDict(from_attributes=True)


# 岗位匹配请求：规定计算一份简历与一个已有岗位的匹配度时需要的数据。
class JobMatchRequest(BaseModel):
    resume_id:int  # 简历编号。
    job_id:int  # 岗位编号。
    city:str=''  # 期望城市；空字符串表示没有城市限制。
    min_pay:int=0  # 最低期望薪资；0表示没有最低薪资限制。

# 岗位定制请求：规定手动粘贴岗位描述时前端必须提交的数据。
class JobAssistRequest(BaseModel):
    resume_id:int=Field(gt=0)  # 简历编号，必须大于0。
    # 岗位描述，长度限制可以拦截过短内容并控制模型费用。
    jd_text:str=Field(min_length=20,max_length=20000)
    job_title:str=Field(min_length=1,max_length=100)  # 岗位名称。
    company:str=Field(min_length=1,max_length=100)  # 公司名称。
    model_config=ConfigDict(
        # 自动去掉所有字符串两端的空格，并拒绝没有声明的额外字段。
        str_strip_whitespace=True,extra='forbid'
    )


# 模型选择的一条候选引用：用编号关联本次提供的经历列表，不要求生成改写。
class AdviceDraft(BaseModel):
    need:str  # 这条建议对应的岗位要求。
    proof_id:int=Field(ge=0)  # 简历证据编号，必须大于或等于0。


# 模型生成的完整定制草稿：尚未经过后端证据编号检查。
class TailorDraft(BaseModel):
    summary:str  # 简历定制建议的总体说明。
    items:list[AdviceDraft]  # 多条带证据编号的建议草稿。
    missing:list[str]  # 模型判断需要补充经历依据的岗位要求，不代表候选人一定不会。


# 已取回经历文字的一条候选引用：编号有效不代表经历支持对应岗位要求。
class RewriteAdvice(BaseModel):
    requirement:str  # 这条建议对应的岗位要求。
    evidence:str  # 后端按编号取回的经历文字；经历列表可能来自AI简历分析。
    rewrite:str  # 兼容原有接口的字段；当前check_draft固定返回空字符串，不传递模型改写。


# 简历定制结果：包含待核对的模型总结、候选引用和待补依据的要求。
class TailorResult(BaseModel):
    summary:str  # 简历定制建议的总体说明。
    suggestions:list[RewriteAdvice]  # 已检查编号的候选引用，未自动核验与岗位要求的语义关联。
    missing_requirements:list[str]  # 模型报告或因引用无效而加入的待补依据要求。


# 招呼语模型结果：限制模型必须返回一段非空文字。
class GreetingResult(BaseModel):
    greeting:str=Field(min_length=1,max_length=300)  # 求职招呼语，长度为1到300个字符。


class Scoreminxi(BaseModel):
    skill:int=Field(ge=0,le=35)
    exp:int=Field(ge=0,le=30) #经历
    role:int=Field(ge=0,le=10) #岗位



# 岗位定制接口最终返回结构：前端按照这个结构展示结果。
class JobAssistResponse(BaseModel):
    resume_id:int  # 本次使用的简历编号。
    score:int=Field(ge=0,le=100)  # 岗位匹配分，范围是0到100。
    parts:Scoreminxi #分项
    matched_skills:list[str]  # 简历已经具备的岗位技能。
    missing_skills:list[str]  # 简历缺少的岗位技能。
    tailoring:TailorResult  # 简历定制建议。
    greeting:str  # 可以人工确认后发送的求职招呼语。
    ai_ok:bool=True  # 模型相关步骤是否正常完成，默认正常。


# 技能匹配结果：记录技能得分、已匹配技能和缺少技能。
class SkillMatchResult(BaseModel):
    score:int  # 技能维度得分。
    matched_skills:list[str]  # 已匹配技能列表。
    missing_skills:list[str]  # 缺少技能列表。


# 关键词匹配结果：记录关键词得分和匹配情况。
class KeywordMatchResult(BaseModel):
    score:int  # 关键词维度得分。
    matched_keywords:list[str]  # 已匹配关键词列表。
    missing_keywords:list[str]  # 缺少关键词列表。

class NeedDraft(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    text: str = Field(min_length=1)
    kind: Literal['技能', '职责', '经验', '学历', '加分']
    start: int = Field(ge=0)
    end: int = Field(ge=0)

class NeedDrafts(BaseModel):
    model_config = ConfigDict(extra='forbid')
    items: list[NeedDraft]



class Need(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    id:int=Field(ge=0)
    text:str=Field(min_length=1)
    kind:Literal['技能', '职责', '经验', '学历', '加分'] 
    quote:str=Field(min_length=1)

class Needs(BaseModel):
    model_config=ConfigDict(extra='forbid')
    items:list[Need]

class Check(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    need_id:int=Field(ge=0)
    status:Literal['有依据', '部分支持', '未找到依据', '待核对']
    proof_ids:list[int]
    note:str=Field(min_length=1)

class Checks(BaseModel):
    model_config=ConfigDict(extra='forbid')
    items:list[Check]


class Report(BaseModel):
    model_config=ConfigDict(extra='forbid')
    needs:list[Need]
    checks:list[Check]
    proofs:list[str]

class ReportBoag(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:int
    title:str
    company:str
    created_at:datetime

class ReportSaved(Report):
    report_id: int

class ReportDeta(ReportBoag):
    resume_id:int
    jd:str
    content:Report

# 岗位要求分析结果：限制模型按五个部分拆解岗位描述。
class JobRequirementResult(BaseModel):
    responsibilities:list[str]  # 岗位职责列表。
    required_skills:list[str]  # 必备技能列表。
    experience:list[str]  # 工作或项目经验要求。
    education:list[str]  # 学历要求。
    bonus_points:list[str]  # 加分项列表。

# 一条职责匹配证据：说明岗位职责与哪条简历经历对应。
class Dutyproof(BaseModel):
    responsibility:str  # 岗位要求的职责。
    resume_evidence:str  # 支持这项职责的简历证据。


# 经历匹配结果：记录职责匹配得分、证据和缺少的职责。
class ExpMatch(BaseModel):
    score:int  # 经历维度得分。
    matches:list[Dutyproof]  # 已找到简历证据的职责列表。
    missing_responsibilities:list[str]  # 简历中没有证据的岗位职责。


# 岗位名称匹配结果：判断求职方向是否与岗位名称一致。
class RoleMatch(BaseModel):
    score:int  # 岗位名称维度得分。
    hit:bool  # 是否匹配成功。
    note:str  # 岗位名称匹配说明。


# 求职偏好匹配结果：记录城市和最低薪资是否符合预期。
class PrefMatch(BaseModel):
    score:int  # 求职偏好维度得分。
    city_ok:bool  # 工作城市是否符合预期。
    pay_ok:bool  # 岗位薪资是否达到最低预期。
    notes:list[str]  # 城市和薪资的中文说明。


# 语义匹配结果：记录文本意思的相似程度和所用模型。
class SemMatch(BaseModel):
    sim:float  # 语义相似度小数。
    model:str  # 计算相似度时使用的模型名称。
    note:str  # 给前端用户看的中文说明。


# 模型用量：像“AI电表”，记录一次模型调用消耗的文本单位数量。
class TokenUse(BaseModel):
    input_tokens:int=0  # 输入用量，例如提示词和简历内容，默认0。
    output_tokens:int=0  # 模型生成回答的用量，默认0。
    total_tokens:int=0  # 输入与输出的总用量，默认0。


# 匹配解释结果：规定模型必须返回总结、理由、缺口和行动建议。
class MatchExplain(BaseModel):
    summary:str  # 匹配情况总结。
    reasons:list[str]  # 后端确认过的匹配理由。
    gaps:list[str]  # 后端确认过的能力缺口。
    actions:list[str]  # 面向求职者的改进建议。


# RAG提问请求：限制问题不能为空、不能过长，也不能携带额外字段。
class RagAsk(BaseModel):
    question:str=Field(min_length=1,max_length=500)  # 用户问题，长度为1到500个字符。
    # 自动去掉问题两端空格，并拒绝未声明字段。
    model_config=ConfigDict(str_strip_whitespace=True,extra='forbid')


# RAG资料来源：保存一段检索文字及其相似度分数。
class RagSrc(BaseModel):
    text:str  # 从知识库检索到的资料原文。
    score:float=Field(ge=-1,le=1)  # 相似度分数，范围是-1到1。


# RAG回答结果：包含回答、可信来源和资料是否足够。
class RagAnswer(BaseModel):
    answer:str  # 模型根据参考资料生成的回答。
    sources:list[RagSrc]  # 后端检索并确认过的资料来源。
    enough:bool  # 是否检索到了参考资料（由后端判定，不采用模型自述）。


# Agent提问请求：规定前端只能提交一个非空目标。
class AgentAsk(BaseModel):
    goal:str=Field(min_length=1,max_length=500)  # 用户希望Agent完成的目标。
    # 自动去掉目标两端空格，并拒绝未声明字段。
    model_config=ConfigDict(str_strip_whitespace=True,extra='forbid')


# Agent回答结果：规定后端向前端返回最终回答文字。
class AgentAnswer(BaseModel):
    answer:str  # Agent完成工具判断和执行后生成的最终回答。


# 岗位匹配接口最终返回结构：集中返回所有评分维度和模型解释。
class JobMatchResponse(BaseModel):
    resume_id:int  # 本次参与匹配的简历编号。
    job_id:int  # 本次参与匹配的岗位编号。
    job_requirements: JobRequirementResult
    current_score:int  # 当前获得的总分。
    current_max_score:int  # 当前已接入评分维度能够获得的最高分。
    skill_match:SkillMatchResult  # 固定技能匹配结果。
    keyword_match:KeywordMatchResult  # 岗位关键词匹配结果。
    required_skill_match:SkillMatchResult  # 模型提取的必备技能匹配结果。
    experience_match:ExpMatch  # 工作或项目经历匹配结果。
    role_match:RoleMatch  # 岗位名称匹配结果。
    pref_match:PrefMatch | None=None  # 求职偏好结果；暂时允许没有。
    sem_match:SemMatch | None=None  # 语义匹配结果；暂时允许没有。
    ai_explain:MatchExplain | None=None  # 模型生成的匹配解释；暂时允许没有。

# `| None`：【语言固定】表示字段既可以有指定类型的数据，也可以为空。
# `=None`：【语言固定】表示调用方没有提供该字段时，默认使用空值。

class ApplyCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    # extra='forbid'：拒绝未声明字段，例如用户偷偷提交 user_id。
    report_id: int = Field(gt=0)


class ApplyUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    status: Literal['待投递', '已投递', '面试中', '已结束']
# Literal列出允许的状态，由Pydantic校验；不在列表中的文字会被拒绝。
    note: str = Field(max_length=2000)

class ApplyOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:int
    user_id:int
    report_id:int
    status:str
    note:str
    created_at:datetime
    updated_at:datetime

class ApplyItem(ApplyOut):
    title: str
    company: str


class QuickJob(BaseModel):
    name:str=Field(min_length=1,max_length=200)
    tags:list[str]=Field(default_factory=list,max_length=30)

class QuickScoreRequest(BaseModel):
    resume_id:int=Field(gt=0)
    jobs:list[QuickJob]=Field(max_length=50)

class QuickScoreItem(BaseModel):
    name:str
    score:int=Field(ge=0,le=100)
    matched:list[str]


class ProfileWork(BaseModel):
    company:str=''
    title:str=''
    period:str=''
    items:list[str]=Field(default_factory=list,max_length=8)


class ProfileProject(BaseModel):
    name:str
    role:str=''
    period:str=''
    stack:str=''
    items:list[str]=Field(default_factory=list,max_length=10)


class ProfileEdu(BaseModel):
    school:str=''
    major:str=''
    degree:str=''
    period:str=''

class ProfileSkill(BaseModel):
    group:str
    text:str


class ResumeProfile(BaseModel):
    name:str=''
    target:str=''
    city:str=''
    phone:str=''
    email:str=''
    link:str=''
    summary:str=''
    skills:list[ProfileSkill]=Field(default_factory=list,max_length=6)
    projects:list[ProfileProject]=Field(default_factory=list,max_length=4)
    works:list[ProfileWork]=Field(default_factory=list,max_length=5)
    education:list[ProfileEdu]=Field(default_factory=list,max_length=3)


class ProfileBuildRequest(BaseModel):
    raw:str=Field(min_length=10,max_length=8000)
    target:str=Field(default='',max_length=50)