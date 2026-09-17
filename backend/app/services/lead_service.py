import re
from collections import Counter
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from pathlib import Path
from datetime import datetime,date
from types import SimpleNamespace

from .job_assist_service import make_report
from .report_service import save_report
from .matching_service import NO_JD_CAP,get_user_resume_analysis,load_targets,read_profile,score_jobs
from ..utils.text import plain_text
from ..models import JobLead,Resume
from ..services.resume_parser import extract_pdf_text
from ..schemas import LeadIn,LeadJdIn,JobAssistRequest


def set_score(row:JobLead,base:int):
    # 插件传来的是标题分：没读过 JD 的岗位最高 59
    row.base_score=base
    row.quick_score=min(base,NO_JD_CAP)


def score_context(db:Session,user,resume_id:int)->dict|None:
    # 打分要用到：简历分析（技能）、简历里的学历和年限、求职方案
    analysis=get_user_resume_analysis(db,resume_id,user.id)
    if analysis is None:
        return None
    try:
        profile=read_profile(load_proofs(db,user.id,resume_id),date.today())
    except (ValueError,OSError):
        return None
    return {'analysis':analysis,'targets':load_targets(user.job_targets,analysis),'profile':profile}


def rescore_rows(rows:list[JobLead],ctx:dict):
    # 每套求职方案各算一次（标题分 + JD 门槛和加分），留分最高的那套；没读过 JD 最高 59
    jobs=[SimpleNamespace(name=row.title,tags=row.tags or [],jd=row.jd_text,salary=row.salary) for row in rows]
    for row,best in zip(rows,score_jobs(ctx['analysis'],ctx['targets'],jobs,ctx['profile'])):
        row.base_score=best['base']
        row.jd_flags=best['flags']
        row.jd_hits=best['hits']
        row.pros=best['pros']
        row.cons=best['cons']
        row.jd_cut=best['cut']
        row.target=best['target']
        row.quick_score=best['score'] if row.jd_text else min(best['score'],NO_JD_CAP)


def save_leads(db:Session,user_id:int,leads:list[LeadIn],ctx:dict|None=None)->dict:
    uniq={lead.url:lead for lead in leads}
    rows={
        row.url:row
        for row in db.query(JobLead).filter(
            JobLead.user_id==user_id,
            JobLead.url.in_(uniq.keys())
        )
    }
    added=0
    updated=0
    rescore=[]
    for url,lead in uniq.items():
        row=rows.get(url)
        changed=False
        if row is None:
            row=JobLead(user_id=user_id,**lead.model_dump())
            set_score(row,lead.quick_score)
            db.add(row)
            added+=1
            rescore.append(row)
        elif row.jd_text is None and (row.base_score if row.base_score is not None else row.quick_score)!=lead.quick_score:
            # 读过 JD 的岗位已经按 JD 算过分，插件再传标题分不覆盖；没读过的标题分变了才更新
            set_score(row,lead.quick_score)
            changed=True
        # 插件这次读到了工资才更新；没读到别把原来的工资清掉
        if lead.salary and row.salary != lead.salary:
            row.salary=lead.salary
            changed=True
        if changed:
            updated+=1
            rescore.append(row)
    # 带了简历编号：新岗位、工资或标题分变了的岗位，按求职方案重新打分（读过 JD 的岗位也会用上新工资）
    if ctx is not None and rescore:
        rescore_rows(rescore,ctx)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    # 已经读过 JD 的链接告诉插件，别再点开读第二遍——重复点详情页最容易被风控
    done=[url for url,row in rows.items() if row.jd_text]
    return {'added':added,'updated':updated,'total':len(uniq),'has_jd':done}


# 排序方式：网页传哪个名字，就用哪一组排序规则。
ORDERS = {
    '分数高': (JobLead.quick_score.desc(), JobLead.id.desc()),
    '分数低': (JobLead.quick_score.asc(), JobLead.id.desc()),
    '最新': (JobLead.id.desc(),),
}

# 岗位池分类：按标题关键词分。一个岗位可以同时属于几类（「AI Agent开发（跨境电商）」既算跨境也算AI）。
# 标题带销售、业务员的只算「销售/业务」；哪类都不沾的，标题带「运营」算「其他运营」，否则算「其他」。
CROSS_BORDER=r'跨境|亚马逊|amazon|tik\s*tok|(?<![a-z])tk(?![a-z])|temu|shein|速卖通|aliexpress|shopee|lazada|独立站|etsy|ebay|沃尔玛|walmart|美客多|ozon|国际站|出海|东南亚|美区|欧洲站|日本站'
# 「产品开发」「市场开发」「客户开发」不是写代码
NOT_DEV=r'(?<!产品)(?<!商品)(?<!市场)(?<!业务)(?<!客户)(?<!渠道)(?<!选品)'
LEAD_KINDS={
    '跨境电商':(CROSS_BORDER,None),
    '国内电商':(r'电商|淘宝|天猫|京东|拼多多|抖店|店铺|旗舰店|直播|1688|国内站',CROSS_BORDER),
    '本地生活':(r'本地生活|团购|到店|美团|点评|外卖|闪购|饿了么|即时零售|门店',None),
    '广告投放':(r'投放|投手|信息流|千川|广告|优化师|竞价',None),
    'AI相关':(r'(?<![a-z])ai(?![a-z])|人工智能|大模型|agent|智能体|aigc|llm|gpt',None),
    '实施/技术支持':(r'实施|技术支持|售前(?:技术|工程|支持|顾问|解决方案)|技术售前|客户成功|交付|部署|erp|saas|数字化',None),
    '自动化/开发':(r'rpa|影刀|自动化|python|'+NOT_DEV+r'开发|研发|全栈|前端|后端|测试|爬虫|程序员|java|算法',None),
    '数据':(r'数据',None),
}
KIND_RULES={name:(re.compile(hit,re.I),re.compile(skip,re.I) if skip else None) for name,(hit,skip) in LEAD_KINDS.items()}
SALES_KIND=re.compile(r'销售|业务员|业务代表|(?<![a-z])bd(?![a-z])|商务拓展|招商|电销|大客户|渠道经理|客户经理',re.I)
KIND_NAMES=[*LEAD_KINDS,'其他运营','销售/业务','其他']
TIER_NAMES=['建议投','可投可不投','待读JD','先不看']


def lead_kinds(title:str)->list[str]:
    title=title or ''
    if SALES_KIND.search(title):
        return ['销售/业务']
    kinds=[name for name,(hit,skip) in KIND_RULES.items() if hit.search(title) and not (skip and skip.search(title))]
    return kinds or (['其他运营'] if '运营' in title else ['其他'])


def lead_tier(score:int,has_jd:bool)->str:
    # 和岗位池页面上每行的分档标签一致：没读 JD 的分数不算数
    if not has_jd:
        return '待读JD'
    if score>=60:
        return '建议投'
    if score>=55:
        return '可投可不投'
    return '先不看'


def list_leads(db:Session,user_id:int,status:str|None=None,
               offset:int=0,limit:int=50,min_score:int=0,
               order:str='分数高',keyword:str='',kind:str='',tier:str='',
               in_jd:bool=False)->tuple[list[JobLead],int,dict]:
    # 先只取编号、标题、分数这几列（JD 正文很大），筛完再按这一页的编号取整行
    q=db.query(JobLead.id,JobLead.title,JobLead.quick_score,JobLead.jd_text.isnot(None)).filter(JobLead.user_id==user_id)
    if status:
        q=q.filter(JobLead.status==status)
    if min_score:
        q=q.filter(JobLead.quick_score>=min_score)
    # 搜索框：空格隔开的每个词都要出现在标题或公司里；勾了「也搜JD正文」再查 JD
    for word in (keyword or '').split():
        like='%'+word.replace('/','//').replace('%','/%').replace('_','/_')+'%'
        cols=[JobLead.title.ilike(like,escape='/'),JobLead.company.ilike(like,escape='/')]
        if in_jd:
            cols.append(JobLead.jd_text.ilike(like,escape='/'))
        q=q.filter(or_(*cols))
    rows=[
        (id,lead_kinds(title),lead_tier(score,bool(has_jd)))
        for id,title,score,has_jd in q.order_by(*ORDERS.get(order, ORDERS['分数高'])).all()
    ]
    # 每个方向后面的数字按当前分档算，每个分档后面的数字按当前方向算
    by_tier=[row for row in rows if not tier or row[2]==tier]
    by_kind=[row for row in rows if not kind or kind in row[1]]
    kind_count=Counter(name for _,names,_ in by_tier for name in names)
    tier_count=Counter(row[2] for row in by_kind)
    ids=[id for id,names,_ in by_tier if not kind or kind in names]
    page=ids[offset:offset+limit]
    found={row.id:row for row in db.query(JobLead).filter(JobLead.id.in_(page))} if page else {}
    facets={
        'kinds':{'全部':len(by_tier),**{name:kind_count[name] for name in KIND_NAMES}},
        'tiers':{'全部':len(by_kind),**{name:tier_count[name] for name in TIER_NAMES}},
    }
    return [found[id] for id in page if id in found],len(ids),facets

def save_jd(db:Session,user_id:int,items:list[LeadJdIn],ctx:dict|None=None)->dict:
    uniq={item.url:item for item in items}
    rows=db.query(JobLead).filter(
        JobLead.user_id==user_id,
        JobLead.url.in_(uniq.keys())
    ).all()
    changed=[]
    for row in rows:
        item=uniq[row.url]
        # 部首字换回普通汉字再存：页面显示和以后打分都用干净的文字
        text=plain_text(item.jd_text)
        if row.jd_text==text:
            continue
        row.jd_text=text
        row.deep_at=None
        row.deep_ok=0
        row.deep_part=0
        row.deep_total=0
        row.report_id=None
        changed.append(row)
    if ctx is not None and changed:
        rescore_rows(changed,ctx)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return {
        'updated':len(changed),
        'missed':len(uniq)-len(rows),
        'items':[
            {
                'url':row.url,
                'score':row.quick_score,
                'base':row.base_score if row.base_score is not None else row.quick_score,
                'hits':row.jd_hits or [],
                'flags':row.jd_flags or [],
                'target':row.target,
                'skip':any(f.startswith('HR超过3天未活跃') for f in (row.jd_flags or [])),
                'reason':next((f for f in (row.jd_flags or []) if f.startswith('HR超过3天未活跃')),None),
            }
            for row in rows
        ],
    }


def rescore_all(db:Session,user_id:int,ctx:dict)->dict:
    rows=db.query(JobLead).filter(JobLead.user_id==user_id).all()
    rescore_rows(rows,ctx)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return {'total':len(rows),'passed':sum(1 for row in rows if row.quick_score>=60)}


def load_proofs(db:Session,user_id:int,resume_id:int)->list[str]:
    resume=db.query(Resume).filter(
        Resume.id==resume_id,
        Resume.user_id==user_id
    ).first()
    if resume is None:
        raise ValueError('简历不存在')
    if resume.content_type!='application/pdf':
        raise ValueError('当前仅支持PDF简历')
    path=Path(__file__).resolve().parents[2]/'uploads'/'resumes'/resume.stored_filename
    return [line.strip() for line in extract_pdf_text(path).splitlines() if line.strip()]

def analyze_next(db:Session,user_id:int,resume_id:int,proofs:list[str],min_score:int=60)->dict:
    base=db.query(JobLead).filter(
        JobLead.user_id==user_id,
        JobLead.jd_text.isnot(None),
        JobLead.deep_at.is_(None),
        JobLead.quick_score>=min_score,
        JobLead.status!='已跳过'
    )
    lead=base.order_by(JobLead.quick_score.desc(),JobLead.id.desc()).first()
    if lead is None:
        return {'analyzed':False,'remaining':0}
    result=make_report(lead.jd_text,proofs)
    row=save_report(db,user_id,JobAssistRequest(
        resume_id=resume_id,
        jd_text=lead.jd_text,
        job_title=lead.title[:100],
        company=(lead.company or '未知')[:100]
    ),result,commit=False)
    lead.deep_ok=sum(1 for c in result.checks if c.status=='有依据')
    lead.deep_part=sum(1 for c in result.checks if c.status=='部分支持')
    lead.deep_total=len(result.checks)
    lead.report_id=row.id
    lead.deep_at=datetime.now()
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return {
        'analyzed':True,
        'remaining':base.count(),
        'lead_id':lead.id,
        'title':lead.title,
        'deep_ok':lead.deep_ok,
        'deep_part':lead.deep_part,
        'deep_total':lead.deep_total
    }


def update_status(db:Session,user_id:int,lead_id:int,status:str):
    lead=db.query(JobLead).filter(
        JobLead.id==lead_id,
        JobLead.user_id==user_id
    ).first()
    if lead is None:
        return None
    lead.status=status
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    db.refresh(lead)
    return lead


def delete_lead(db:Session,user_id:int,lead_id:int)->str:
    lead=db.query(JobLead).filter(
        JobLead.id==lead_id,
        JobLead.user_id==user_id
    ).first()
    if lead is None:
        return '不存在'
    if lead.status=='已投递':
        return '已投递'
    db.delete(lead)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return '成功'

def delete_unapplied(db:Session,user_id:int,status:str|None)->int:
    q=db.query(JobLead).filter(
        JobLead.user_id==user_id,
        JobLead.status!='已投递'
    )
    if status:
        q=q.filter(JobLead.status==status)
    n=q.delete(synchronize_session=False)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return n


def delete_without_jd(db:Session,user_id:int)->int:
    # 只清理当前用户尚未读取岗位介绍、且没有投递过的岗位。
    n=db.query(JobLead).filter(
        JobLead.user_id==user_id,
        JobLead.jd_text.is_(None),
        JobLead.status!='已投递'
    ).delete(synchronize_session=False)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return n

def skip_below(db:Session,user_id:int,below:int)->int:
    n=db.query(JobLead).filter(
        JobLead.user_id==user_id,
        JobLead.quick_score<below,
        JobLead.status.in_(['新抓取','待投递'])
    ).update({'status':'已跳过'},synchronize_session=False)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return n

def mark_above(db:Session,user_id:int,above:int)->int:
    n=db.query(JobLead).filter(
        JobLead.user_id==user_id,
        JobLead.quick_score>=above,
        JobLead.status.in_(['新抓取','已跳过'])
    ).update({'status':'待投递'},synchronize_session=False)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return n

def unmark_all(db:Session,user_id:int)->int:
    n=db.query(JobLead).filter(
        JobLead.user_id==user_id,
        JobLead.status=='待投递'
    ).update({'status':'新抓取'},synchronize_session=False)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return n


def unread_jd_query(db:Session,user_id:int):
    # 值得补读 JD 的岗位：没读过 JD、没投递也没跳过。标题阶段已经判 0 分的不读——读了 JD 也还是 0 分
    return db.query(JobLead).filter(
        JobLead.user_id==user_id,
        JobLead.jd_text.is_(None),
        JobLead.status.notin_(['已投递','已跳过']),
        JobLead.quick_score>0
    )


def list_unread_jd(db:Session,user_id:int,limit:int)->dict:
    # 标题分高的先读
    q=unread_jd_query(db,user_id)
    rows=q.order_by(JobLead.quick_score.desc(),JobLead.id.desc()).limit(limit).all()
    return {'total':q.count(),'items':rows}


def lead_stats(db:Session,user_id:int)->dict:
    rows=db.query(JobLead).filter(JobLead.user_id==user_id).all()
    deep=[row for row in rows if row.deep_at]
    return {
        'total':len(rows),
        'with_jd':sum(1 for row in rows if row.jd_text),
        'without_jd':sum(1 for row in rows if not row.jd_text and row.status!='已投递'),
        'passed':sum(1 for row in rows if row.quick_score>=60),
        'analyzed':len(deep),
        'to_apply':sum(1 for row in rows if row.status=='待投递'),
        'applied':sum(1 for row in rows if row.status=='已投递'),
        'skipped':sum(1 for row in rows if row.status=='已跳过'),
        'high':sum(1 for row in rows if row.quick_score>=80),
        'mid':sum(1 for row in rows if 60<=row.quick_score<80),
        'low':sum(1 for row in rows if row.quick_score<60),
        'need_total':sum(row.deep_total for row in deep),
        'need_ok':sum(row.deep_ok for row in deep),
        'need_part':sum(row.deep_part for row in deep),
        'unread_jd':sum(1 for row in rows if not row.jd_text and row.status not in ('已投递','已跳过') and row.quick_score>0),
    }
