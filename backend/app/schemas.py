from pydantic import BaseModel,ConfigDict
from datetime import datetime
# 数据验证数据格式转换

class JobSchema(BaseModel):
    id:int
    title:str
    company:str
    salary:str
    location:str
    skills:str
    description:str
    class Config:
        from_attributes=True

class UserCreate(BaseModel):

    username:str

    email:str

    password:str
# UserCreate：规定前端可以提交什么。
# UserResponse：规定后端可以返回什么。
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
    strengths:list[str]
    improvement_suggestions:list[str]
    recommended_positions:list[str]

class ResumeAnalysisResponse(ResumeAIAnalysis):
     id:int
     created_at:datetime

     model_config=ConfigDict(
          from_attributes=True
     )

class JobMatchRequest(BaseModel):
     resume_id:int
     job_id:int

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

class JobMatchResponse(BaseModel):
     resume_id:int
     job_id:int
     current_score:int
     current_max_score:int
     skill_match:SkillMatchResult
     keyword_match:KeywordMatchResult

