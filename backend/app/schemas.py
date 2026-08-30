from pydantic import BaseModel,ConfigDict
from datetime import datetime
# 数据验证数据格式转换

#  岗位数据返回格式
class JobSchema(BaseModel):
    id:int
    title:str
    company:str
    salary:str
    location:str
    skills:str
    description:str
    model_config=ConfigDict(from_attributes=True)

# 用户注册时，前端提交的数据格式
class UserCreate(BaseModel):

    username:str

    email:str

    password:str
# UserCreate：规定前端可以提交什么。
# UserResponse：规定后端可以返回什么。
# 用户信息返回格式
class UserResponse(BaseModel):
        id:int
        username:str
        email:str
        model_config=ConfigDict(from_attributes=True)

class UserLogin(BaseModel):
     username:str
     password:str

class ResumeResponse(BaseModel):
     id:int
     original_filename:str
     content_type:str
     file_size:int
     created_at:datetime

     model_config=ConfigDict(from_attributes=True)

class ResumeAIAnalysis(BaseModel):
    resume_id:int
    summary:str
    skills:list[str]
    work_experience:list[str]
    strengths:list[str]
    improvement_suggestions:list[str]
    recommended_positions:list[str]
    ai_ok:bool=True

class ResumeAnalysisResponse(ResumeAIAnalysis):
     id:int
     created_at:datetime

     model_config=ConfigDict(
          from_attributes=True
     )

# 岗位匹配请求
class JobMatchRequest(BaseModel):
     resume_id:int
     job_id:int
     city:str=''
     min_pay:int=0

class SkillMatchResult(BaseModel):
     score:int
     matched_skills:list[str]
     missing_skills:list[str]

class KeywordMatchResult(BaseModel):
     score:int
     matched_keywords:list[str]
     missing_keywords:list[str]

class JobRequirementResult(BaseModel):
     responsibilities: list[str]
     required_skills: list[str]
     experience: list[str]
     education: list[str]
     bonus_points: list[str]

# 职责证据 为什么判定匹配
class Dutyproof(BaseModel):
     responsibility:str
     resume_evidence:str
# 岗位要求的职责。
class ExpMatch(BaseModel):
     score:int
     matches:list[Dutyproof]
     missing_responsibilities:list[str]

class RoleMatch(BaseModel):
     score:int
     hit:bool
     note:str

# 规定偏好匹配结果
class PrefMatch(BaseModel):
     score:int
     city_ok:bool
     pay_ok:bool
     notes:list[str]

# 规定后端返回的语义匹配结果必须包含相似度、模型名称和中文说明。
# 以后 Vue 可以稳定读取语义结果，不需要猜后端返回什么。
class SemMatch(BaseModel):
     sim:float
     # sim：相似度，必须是小数。
     model:str
     # model：记录使用了哪个AI模型，必须是文字。
     note:str
     # note：给用户看的中文说明。


# 这段代码像“AI电表”，负责记录一次AI调用用了多少资源。
class TokenUse(BaseModel):
     input_tokens:int=0
     # 输入Token数量，例如提示词和简历内容。
     output_tokens:int=0
     # AI生成回答消耗的Token数量。
     total_tokens:int=0
     # 本次调用的总Token数量。


# 【整段代码作用】：规定大模型的岗位推荐解释必须返回哪些内容。
# 【在项目中的用途】：以后Vue可以稳定展示推荐理由、能力缺口和简历优化建议
class MatchExplain(BaseModel):
     summary:str
     # 总结
     reasons:list[str]
     # 推荐理由
     gaps:list[str]
     # 能力缺口
     actions:list[str]
     # 行动建议

# 给RAG回答准备一个固定“快递箱”，
# 箱子里必须包含回答、资料来源、资料是否足够。
class RagAnswer(BaseModel):
     # RagAnswer：【自己命名】，意思是“RAG回答”
     answer:str
     # answer：【自己命名】，回答内容。
     sources:list[str]
     # sources：【自己命名】，中文是“资料来源”
     enough:bool
     # enough：【自己命名】，中文是“资料是否足够”。

# 岗位匹配接口
class JobMatchResponse(BaseModel):
     resume_id:int
     job_id:int
     current_score:int
     current_max_score:int
     skill_match:SkillMatchResult
     keyword_match:KeywordMatchResult
     required_skill_match:SkillMatchResult
     experience_match:ExpMatch
     role_match:RoleMatch
     pref_match:PrefMatch | None=None
     sem_match:SemMatch | None=None
     ai_explain:MatchExplain | None=None
#      | None：【语言固定】，暂时允许没有数据。
# =None：当前评分函数还没接入时不让旧接口报错。

