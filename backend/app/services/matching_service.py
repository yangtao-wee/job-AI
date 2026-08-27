from ..schemas import SkillMatchResult,KeywordMatchResult
from sqlalchemy.orm import Session
from ..models import  Resume,ResumeAnalysis

JOB_KEYWORDS = [
    'Python','FastAPI','MySQL','Redis',
    'Docker','RAG','Agent','Vue'
]

# 合并函数
def merge_job_skills(
        job_skills:str,
        ai_required_skills:list[str]
)->list[str]:
    manual_skills = job_skills.split(',')
    all_skills=manual_skills + ai_required_skills
    return sorted({
        skill.strip().lower()
        for skill in all_skills
        if skill.strip()
    })

def calculate_skill_score(
        resume_skill:list[str],
        job_skills:list[str]
)->SkillMatchResult:
    resume_set = {skill.strip().lower() for skill in resume_skill}
    job_set = {
        skill.strip().lower()
        for skill in job_skills
        if skill.strip()
    }
    matched_skills = resume_set & job_set
    if not job_set:
        return SkillMatchResult(
            score=0,
            matched_skills=[],
            missing_skills=[]
        )
    return  SkillMatchResult(
        score=round(len(matched_skills)/len(job_set)*35),
        matched_skills=sorted(matched_skills),
        missing_skills=sorted(job_set - resume_set)
    )
# sorted()：【语言固定】，把技能按固定顺序排列，方便测试和展示
    # 【skill自己命名】，循环中暂时代表一个技能。
    # strip()：删除文字两边的空格。
    # lower()：统一转换成小写。
    # split(',')：按照英文逗号拆开。
    # &：【语言固定】，计算两个集合的交集。
#     len()：【语言固定】，计算数量。
# round()：【语言固定】，四舍五入。
# * 35：这是【项目规则】，因为技能维度最高35分，可以根据测试结果调整。

def get_user_resume_analysis(
        db:Session,
        resume_id:int,
        user_id:int
)->ResumeAnalysis | None:
    return(
    db.query(ResumeAnalysis)
    .join(Resume,Resume.id == ResumeAnalysis.resume_id)
    # join()：【第三方库】，连接简历表与分析表。
    .filter(
        ResumeAnalysis.resume_id == resume_id,
        Resume.user_id == user_id
    )
    .first()
)

def extract_job_keywords(description:str)->list[str]:
    normalized_description = description.lower()
    # lower()：【语言固定的字符串方法】，统一转成小写。
    return[
        keyword
        for keyword in JOB_KEYWORDS
        if keyword.lower() in normalized_description
#         - for、in：【语言固定】。
# - 依次检查词表中的每个技术词。
# if keyword.lower() in normalized_description
# - 如果关键词出现在岗位描述中，就保留它。
# - 删除这个条件后，系统会把所有关键词都当成岗位要求。
    ]

def calculate_keyword_score(
        resume_skills:list[str],
        job_description:str
)->KeywordMatchResult:
    job_keywords = set(extract_job_keywords(job_description))
    # set()：【语言固定】，转换成集合并自动去重。
    resume_keywords = {skill.lower() for skill in resume_skills}
    matched_keywords = {
        keyword for keyword in job_keywords
        if keyword.lower() in resume_keywords
    }
    if not job_keywords:
        return KeywordMatchResult(
            score=0,matched_keywords=[],missing_keywords=[]
        )
    return KeywordMatchResult(
        score=round(len(matched_keywords) / len(job_keywords)*10),
        matched_keywords=sorted(matched_keywords),
        missing_keywords=sorted(job_keywords - matched_keywords)
    )

def calculate_required_skill_score(
        resume_skills:list[str],
        required_skills:list[str]
)->SkillMatchResult:
    resume_set ={skill.strip().lower() for skill in resume_skills}
    required_set={skill.strip().lower() for skill in required_skills if skill.strip()}
    matched_skills = resume_set & required_set
    # &：【语言固定】，计算两个集合的交集。
    if not required_set:
        return SkillMatchResult(score=0,matched_skills=[],missing_skills=[])
    return SkillMatchResult(score=round(len(matched_skills)/len(required_set)*15),
        matched_skills=sorted(matched_skills),
        missing_skills=sorted(required_set-resume_set)
        )