from sqlalchemy.orm import Session
import re
# re【Python自带】，正则表达式工具，负责从文字中寻找数字。
from ..schemas import SkillMatchResult,KeywordMatchResult,ExpMatch,Dutyproof,RoleMatch,PrefMatch
from ..models import  Resume,ResumeAnalysis

JOB_KEYWORDS = [
    'Python','FastAPI','MySQL','Redis',
    'Docker','RAG','Agent','Vue'
]

EXPERIENCE_KEYWORDS = JOB_KEYWORDS + ['AI','接口','数据库','部署','测试','需求','文档']
ROLE_KEYS=['Python','Vue','AI','后端','前端','产品']
def find_resume_evidence(
        responsibility:str,work_experience:list[str]
)->str | None:
    responsibility_lower = responsibility.lower()
    for evidence in work_experience:
        evidence_lower=evidence.lower()
        has_shared_keyword = any(
            # any检查双方是否至少拥有一个相同关键词。
            keyword.lower() in responsibility_lower
            and keyword.lower() in evidence_lower
            # in/and【语言固定】关键词必须同时出现在岗位职责和简历经历中。
            for keyword in EXPERIENCE_KEYWORDS
        )
        if has_shared_keyword:
            return evidence
    return None

def calculate_experience_score(
        work_experience:list[str],responsibilities:list[str]
)->ExpMatch:
    if not responsibilities:
        return ExpMatch(score=0,matches=[],missing_responsibilities=[])
    matches,missing=[],[]
    for responsibility in responsibilities:

        evidence = find_resume_evidence(responsibility,work_experience)
        if evidence:
            matches.append(Dutyproof(responsibility=responsibility,resume_evidence=evidence))
        else:
            missing.append(responsibility)
    return ExpMatch(
        score=round(len(matches)/len(responsibilities)*30),
        matches=matches,missing_responsibilities=missing)


# 拿岗位名称＋拿AI给简历推荐的岗位方向
def score_role(title:str,roles:list[str])->RoleMatch:
    text=''.join(roles).lower()
    # join负责连接文字
    hits=[
        key for key in ROLE_KEYS
        if key.lower() in title.lower() and key.lower() in text
    ]
    if hits:
        return RoleMatch(
            score=10,hit=True,note=f"共同方向:{','.join(hits)}")
    return RoleMatch(score=0,hit=False,note='岗位方向未匹配')

# 偏好评分函数
def score_pref(
        job_city:str, pay_text:str,
        city:str, min_pay:int
)->PrefMatch:
    nums=[int(n) for n in re.findall(r'\d+',pay_text)]
    # re.findall(...)：【Python自带】，从薪资文字中找出全部数字。
    # r'\d+'：【固定规则】，表示寻找连续数字。
    # int(n)：【语言固定】，把文字数字转换成真正的整数。
    top=max(nums,default=0)
    # max()：【语言固定】，取得最大数字。
    # default=0：没有找到数字时使用0，避免程序报错。
    city_ok=not city or city in job_city
    # city in job_city：检查期望城市是否出现在岗位城市中
    pay_ok=min_pay<=0 or top>=min_pay
    score=(5 if city_ok else 0)+(10 if pay_ok else 0)
    notes=[
        f"城市：{'符合'if city_ok else '不符合'}",
        f"薪资：{'符合'if pay_ok else '不符合'}"
    ]
    return PrefMatch(
        score=score,city_ok=city_ok,pay_ok=pay_ok,notes=notes
    )

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
    resume_set = {skill_name(skill) for skill in resume_skill}
    job_set = {
        skill_name(skill)
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


def skill_name(text:str)->str:
    name=text.strip().lower()
    names={
        'python编程':'python',
        'python语言':'python',
        'vue.js':'vue'
    }
    return names.get(name,name)
# 字典的 get() 用来查找。第一个 name 是要查什么，第二个是查不到时返回什么。

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