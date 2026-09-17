import pytest
from types import SimpleNamespace
from datetime import date
from app.utils.pay import decode_pay,parse_pay_range
from app.utils.text import plain_text
from app.schemas import QuickJob
from app.services.matching_service import good_hits,calculate_required_skill_score,calculate_skill_score,merge_job_skills,calculate_experience_score,score_role,score_pref,build_job_requirements,calculate_keyword_score,quick_score,read_edu,read_years,edu_cut,exp_cut,read_fulltime_edu,read_elite,screen_jd,screen_pay,business_hits,requirement_hits,title_rule_match,apply_jd,read_active,load_targets,score_jobs,read_age


def test_partial_match():
    result = calculate_required_skill_score(
        ['Python','FastAPI','Vue3'],
        ['Python','FastAPI','RAG']
    )
    assert result.score == 10

def test_empty_requirements():
    result = calculate_required_skill_score(['Python'],[])
    assert result.score==0

def test_no_match():
    result = calculate_required_skill_score(['Vue3'],['Python'])
    assert result.score==0

def test_merged_skills_are_scored_one():
    merged_skills = merge_job_skills(
        'Python,FastAPI', ['Python','RAG']
    )
    result = calculate_skill_score(
        ['Python','FastAPI','Vue3'],merged_skills
    )
    assert merged_skills == ['fastapi','python','rag']
    assert  result.score==23

def test_exp_partial():
    result=calculate_experience_score(
        ['使用FastAPI开发Python接口'],
        ['负责Python接口开发','负责Docker部署']
    )
    assert result.score==15
    assert len(result.matches)==1
    assert result.missing_responsibilities==['负责Docker部署']

def test_exp_empty():
    result = calculate_experience_score(['负责vue页面'],[])
    assert result.score==0

def test_role_hit():
    res=score_role('Python开发工程师',['Python后端开发工程师'])
    assert res.score==10
    assert res.hit is True
    assert res.note=='共同方向:Python'

def test_role_miss():
    res=score_role('销售经理',['Python后端开发工程师'])
    assert res.score==0
    assert res.hit is False

def test_pref_hit():
    res=score_pref('深圳','15-20K','深圳',18)
    assert res.score==15

def test_pref_miss():
    res=score_pref('广州','12-15K','深圳',18)
    assert res.score==0

def test_pay_equal():
    res=score_pref('深圳','15-20K','深圳',20)
    assert res.pay_ok is True

def test_skill_names():
    result = calculate_skill_score(
        ['Python编程','Vue.js'],
        ['Python语言','Vue','Docker']
    )
    assert result.score==23
    assert result.matched_skills==['python','vue']
    assert result.missing_skills==['docker']

def test_split_skills():
    result = calculate_skill_score(
        ['HTML/CSS/JavaScript'],
        ['Vue', 'JavaScript', 'CSS']
    )
    assert result.score == 23
    assert result.matched_skills == ['css', 'javascript']
    assert result.missing_skills == ['vue']


def test_skill_state():
    result=calculate_skill_score(
        ['正在学习Python','不会Docker'],
        ['Python','Docker']
    )
    assert result.score==0
    assert result.matched_skills==[]
    assert result.missing_skills==['docker','python']


# 关键词评分也应识别别名，保留原有返回文字的大小写。
def test_keyword_names():
    result = calculate_keyword_score(
        [' Python编程 ', 'Vue.js'], '要求Python、Vue和Docker'
    )
    assert result.score == 7
    assert result.matched_keywords == ['Python', 'Vue']
    assert result.missing_keywords == ['Docker']


# 同一要求的两个名称只能算一项，避免扩大分母而压低得分。
def test_required_names():
    result = calculate_required_skill_score(
        ['Python编程', 'Vue.js'],
        ['Python', 'Python语言', 'Vue', 'Docker', '   ']
    )
    assert result.score == 10
    assert result.matched_skills == ['python', 'vue']
    assert result.missing_skills == ['docker']


# 合并手填技能与AI提取技能时，先统一名称，再去重。
def test_merge_names():
    result = merge_job_skills(
        'Python编程,Vue.js, ', ['Python语言', 'Vue', '   ']
    )
    assert result == ['python', 'vue']


# 其余两个评分入口也不能把这两个状态描述当成技能命中。
def test_other_states():
    skills = ['正在学习Python', '不会Docker']
    keyword = calculate_keyword_score(skills, '要求Python和Docker')
    required = calculate_required_skill_score(skills, ['Python', 'Docker'])
    assert keyword.score == required.score == 0
    assert keyword.matched_keywords == required.matched_skills == []
    assert keyword.missing_keywords == ['Docker', 'Python']
    assert required.missing_skills == ['docker', 'python']


# 共同的宽泛词不足以给技术职责加分；未命中不等于候选人一定不会。
@pytest.mark.parametrize('work,need', [
    ('运用AI工具批量生成营销短视频', '负责AI平台架构设计'),
    ('负责客户接口沟通', '负责FastAPI接口开发'),
    ('整理客户数据库资料', '负责MySQL数据库性能优化'),
    ('部署门店运营活动', '负责Docker部署'),
    ('测试营销文案效果', '负责Python自动化测试'),
    ('收集客户需求', '根据需求开发FastAPI服务'),
    ('编写运营文档', '编写Redis技术文档'),
])
def test_exp_wide(work, need):
    result = calculate_experience_score([work], [need])
    assert result.score == 0
    assert result.matches == []
    assert result.missing_responsibilities == [need]


# 收紧规则后，明确技术词仍能命中，并返回原经历，不改写原文。
@pytest.mark.parametrize('work,need', [
    ('使用Python开发数据脚本', '负责Python脚本开发'),
    ('使用fastapi开发用户接口', '负责FastAPI接口开发'),
    ('使用Docker部署服务', '负责Docker部署'),
])
def test_exp_tech(work, need):
    result = calculate_experience_score([work], [need])
    assert result.score == 30
    assert len(result.matches) == 1
    assert result.matches[0].responsibility == need
    assert result.matches[0].resume_evidence == work
    assert result.missing_responsibilities == []

def test_exp_learning_is_not_work():
    work = '目前正在自学Python和RPA，目标是用自动化脚本处理数据报表'
    need = '负责使用Python和FastAPI开发AI求职Agent，接入RAG检索能力'

    result = calculate_experience_score([work], [need])

    assert result.score == 0
    assert result.matches == []
    assert result.missing_responsibilities == [need]


@pytest.mark.parametrize('work', [[], ['   ']])
def test_exp_no_work(work):
    result = calculate_experience_score(work, ['负责Python接口开发'])
    assert result.score == 0
    assert result.matches == []
    assert result.missing_responsibilities == ['负责Python接口开发']


# 方向词既要排除宽泛AI误判，也要保留真实存在的全栈方向线索。
@pytest.mark.parametrize('title,roles,score,note', [
    ('AIAgent全栈开发工程师', ['AI驱动的新媒体运营专家'], 0, '岗位方向未匹配'),
    ('AIAgent全栈开发工程师',
     ['AI驱动的新媒体运营专家', '数据分析师', '全栈开发工程师'], 10, '共同方向:全栈'),
    ('AIAgent全栈开发工程师', ['全栈开发工程师'], 10, '共同方向:全栈'),
    ('AI产品经理', ['产品经理'], 10, '共同方向:产品'),
    ('Vue前端工程师', ['Vue前端开发'], 10, '共同方向:Vue,前端'),
    ('AIAgent全栈开发工程师', [], 0, '岗位方向未匹配'),
])
def test_role_keys(title, roles, score, note):
    result = score_role(title, roles)
    assert result.score == score
    assert result.hit is (score > 0)
    assert result.note == note


def test_build_job_requirements():
    result = build_job_requirements(
        'Python,FastAPI',
        '负责Python接口开发；负责FastAPI服务部署。'
    )

    assert result.required_skills == ['fastapi', 'python']
    assert result.responsibilities == [
        '负责Python接口开发',
        '负责FastAPI服务部署'
    ]

def test_quick_score(monkeypatch):
    # 用二维假向量表达「方向」：第一维=电商运营，第二维=剪辑
    VEC = {
        'AI电商运营': [1.0, 0.0],     # 我要的方向
        'AI剪辑师': [0.2, 1.0],       # 挂着 AI 的名，本质是剪辑
        '短视频剪辑师': [0.0, 1.0],   # 纯剪辑（AVOID_ROLES 里的锚点）
        'AI应用工程师（电商方向）': [1.0, 0.0],  # 向量再像，标题是技术岗也不要
    }
    monkeypatch.setattr(
        'app.services.matching_service.embed_many',
        lambda texts: {t: VEC.get(t, [0.0, 0.0]) for t in texts}
    )
    analysis = SimpleNamespace(
        skills=['Python'],
        recommended_positions=['AI电商运营']
    )
    jobs = [
        QuickJob(name='AI电商运营', tags=['Python', '本科', '1年以内']),
        QuickJob(name='AI剪辑师', tags=['本科', '1-3年']),
        QuickJob(name='AI应用工程师（电商方向）', tags=[]),
    ]
    result = quick_score(analysis, jobs)
    assert [item.score for item in result] == [75, 0, 0]
    assert result[0].matched == ['python']

def test_quick_score_rescue(monkeypatch):
    # 三个岗位向量完全一样，都更像「客户经理」；方向用不在 TITLE_RULES 里的名字，走语义判断
    # 区别：标题带「运营」跳过反向锚点；带「运营」但又是「开发」岗，照样检查
    VEC = {
        '网店运营': [1.0, 0.0],
        '电商运营助理（客户对接）': [0.6, 0.8],
        '电商运营开发': [0.6, 0.8],
        'AI客户专员': [0.6, 0.8],
        '客户经理': [0.0, 1.0],
    }
    monkeypatch.setattr(
        'app.services.matching_service.embed_many',
        lambda texts: {t: VEC.get(t, [0.0, 0.0]) for t in texts}
    )
    analysis = SimpleNamespace(skills=['Python'], recommended_positions=['网店运营'])
    jobs = [QuickJob(name=n, tags=[]) for n in ('电商运营助理（客户对接）', '电商运营开发', 'AI客户专员')]
    result = quick_score(analysis, jobs)
    assert [item.score for item in result] == [42, 35, 35]
    assert all(item.read_jd for item in result)

def test_read_profile():
    lines = [
        '湖北工业大学（成人本科）  本科  计算机及应用 2024-2026',
        '武汉工程职业技术学院（全日制）  大专  计算机应用 2018-2022',
        '上海某某有限公司  新媒体运营 2023.10-2026.07',
        'AI Job Agent｜智能求职助手  2026.07-至今',
    ]
    assert read_edu(lines) == 3
    assert read_years(lines, date(2026, 9, 1)) == 2.75
    assert read_years(['自学 Python'], date(2026, 9, 1)) is None
    # 简历写了年龄才判断 JD 的年龄要求
    assert read_age(['姓名：张三  26岁  深圳'], date(2026, 9, 1)) == 26
    assert read_age(['出生年月：1998.05'], date(2026, 9, 1)) == 28
    assert read_age(lines, date(2026, 9, 1)) is None


def test_edu_exp_cut():
    assert edu_cut(['硕士', '1-3年'], 3) == 20
    assert edu_cut(['大专'], 3) == 0
    assert edu_cut(['博士'], 0) == 0
    # 标签要的年限达到经验上限，直接扣 40
    assert exp_cut(['本科', '5-10年'], 3) == 40
    assert exp_cut(['3-5年'], 3) == 40
    assert exp_cut(['1-3年'], 3) == 0
    assert exp_cut(['1-3年'], 1) == 40
    assert exp_cut(['1年以内'], 1) == 0
    assert exp_cut(['3-5年'], None) == 0

def test_screen_jd():
    p = {'edu': 3, 'full': 2, 'elite': False, 'years': 2.75}
    # 标签写「经验不限」，JD 里却要 3 年；「2.3 年」是序号 2 + 3 年
    jd = '1、统招本科及以上学历\n2、985/211背景优先\n2.3 年以上电商运营经验，有亚马逊经验优先\n4、精通 Excel 数据透视表'
    flags, cut = screen_jd(jd, ['经验不限', '本科'], p)
    # 「精通」可以及格，不再标出来
    assert flags == ['要全日制本科', '要3年电商经验']
    # 「3 年以上电商运营经验」「精通 Excel」写得太深，这两项不算加分
    assert cut == 0
    assert apply_jd(80, flags, cut) == 50


def test_quick_score_target_junior(monkeypatch):
    # 三维假向量：软件实施 / RPA实施 / Python自动化
    VEC = {
        '软件实施工程师': [1.0, 0.0, 0.0], '软件工程师': [1.0, 0.0, 0.0],
        'RPA实施工程师': [0.0, 1.0, 0.0], 'RPA实施助理': [0.0, 1.0, 0.0],
        'Python自动化': [0.0, 0.0, 1.0], 'Python开发工程师': [0.0, 0.0, 1.0],
    }
    monkeypatch.setattr(
        'app.services.matching_service.embed_many',
        lambda texts: {t: VEC.get(t, [0.0, 0.0, 0.0]) for t in texts}
    )
    analysis = SimpleNamespace(skills=[], recommended_positions=[])
    a = SimpleNamespace(name='A', positions=['软件实施工程师', 'Python自动化'], junior=['RPA实施工程师'], max_years=1, good_words=['助理'])
    jobs = [
        QuickJob(name='RPA实施工程师', tags=[]),        # 最像「只投初级」的方向，标题不是初级 → 0
        QuickJob(name='RPA实施助理', tags=['1-3年']),   # 助理可以；标签 1 年起达到上限 1 年，扣 40
        QuickJob(name='RPA实施助理', tags=['经验不限']),
        QuickJob(name='Python开发工程师', tags=[]),     # 开发岗，但最像的是自动化方向 → 照常打分
        QuickJob(name='软件工程师', tags=[]),           # 开发岗，最像的却是「软件实施」→ 0
    ]
    result = quick_score(analysis, jobs, target=a)
    assert [item.score for item in result] == [35, 0, 75, 70, 35]
    assert [item.read_jd for item in result] == [True, False, True, True, True]
    # 方案里全是运营方向：技术岗标题直接 0 分
    b = SimpleNamespace(name='B', positions=['电商运营'], junior=[], max_years=3, good_words=[])
    assert quick_score(analysis, [QuickJob(name='Python开发工程师', tags=[])], target=b)[0].score == 0


def test_score_jobs_picks_best_target(monkeypatch):
    monkeypatch.setattr(
        'app.services.matching_service.embed_many',
        lambda texts: {t: [1.0, 0.0] for t in texts}
    )
    analysis = SimpleNamespace(skills=[], recommended_positions=[])
    targets = load_targets([
        {'name': 'A', 'positions': ['AI运营'], 'max_years': 1},
        {'name': 'B', 'positions': ['电商运营'], 'max_years': 3},
    ], analysis)
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 2.75}
    jobs = [
        SimpleNamespace(name='电商运营助理', tags=[], jd='2年以上抖音运营经验'),  # A 上限 1 年不符合，B 符合
        SimpleNamespace(name='电商运营助理', tags=[], jd=None),                  # 两套一样高，留第一套
    ]
    best = score_jobs(analysis, targets, jobs, p)
    assert [(b['target'], b['score']) for b in best] == [('B', 72), ('A', 70)]
    assert best[0]['flags'] == []


def test_screen_jd_good_words():
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 3.0}
    t = SimpleNamespace(max_years=3, good_words=['经验不限', '提供培训', '接受转行'])
    # 「经验不限」在标签里已经加过；JD 里「系统培训」「转行」合起来最多 10 分，所以这里只再加 5
    assert screen_jd('公司提供系统培训，欢迎转行', ['经验不限'], p, '电商运营助理', t) == ([], -5)


def test_screen_jd_ops_ok():
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 2.75}
    # 1-3 年、2 年以上都低于 3 年；「精通者优先」「无需电话销售」不算硬要求
    jd = ('1-3年抖音运营经验\n2年以上工作经验\n精通者优先\n无需电话销售\n'
          '熟练使用 ChatGPT、Python 提升效率\n负责抖音团购、达人合作和数据复盘')
    flags, cut = screen_jd(jd, ['1-3年'], p)
    # Python、电商运营、数据分析、大模型 API 四个不同能力项分别计一次。
    # 「熟练使用 ChatGPT、Python 提升效率」是 AI 提效信号，再加 10 分
    assert (flags, cut) == ([], -18)
    assert apply_jd(60, flags, cut) == 78


def test_screen_jd_phone_cert():
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 3.0}
    jd = '每天通过电话、微信等方式联系商家\n须持有电子商务师证书'
    flags, cut = screen_jd(jd, [], p)
    assert flags == ['要打电话', '要证书']
    assert apply_jd(90, flags, cut) == 50


def test_screen_jd_content_title():
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 3.0}
    # 内容 / 新媒体类：JD 没写 AI 或自动化工具就压到 50，写了照常加分
    assert screen_jd('负责公众号和小红书内容更新', [], p, '新媒体运营') == (['内容岗没要求AI工具'], 0)
    assert apply_jd(85, ['内容岗没要求AI工具'], 0) == 50
    assert screen_jd('用 Coze 搭建内容自动化工作流', [], p, 'AI内容运营') == ([], -13)


def test_read_fulltime_edu():
    lines = [
        '湖北工业大学（成人本科）  本科  计算机及应用 2024-2026',
        '武汉工程职业技术学院（全日制）  大专  计算机应用 2018-2022',
    ]
    assert read_fulltime_edu(lines) == 2
    assert read_elite(lines) is False


def test_screen_jd_active():
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 3.0}
    allowed = '负责Python开发\n唐女士\n3日内活跃\n和生创新技术 · HR'
    stale = '负责Python开发\n唐女士\n本周活跃\n和生创新技术 · HR'
    fresh = '负责Python开发\n唐女士\n今日活跃\n旦品在线 · 招聘者'
    # 3日内活跃（包括 3 日）：标出来、扣 5 分，不拦
    assert screen_jd(allowed, [], p) == (['HR3日内活跃'], 3)
    assert apply_jd(80, ['HR3日内活跃'], 3) == 77
    flags, cut = screen_jd(stale, [], p)
    assert flags == ['HR超过3天未活跃（本周活跃）']
    assert cut == -2
    assert apply_jd(80, flags, cut) == 0
    # 写了 Python，只命中一个能力项，计 2 分。
    assert screen_jd(fresh, [], p) == ([], -2)
    assert read_active('没有招聘者信息') is None


def test_screen_jd_sales():
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 3.0}
    sales = '负责通过地推获取潜在客户信息\n底薪5000+提成'
    ads = '优化广告出价，降低获客成本\n前端部门享有高提成'
    flags, cut = screen_jd(sales, [], p)
    assert flags == ['疑似销售岗']
    assert apply_jd(80, flags, cut) == 50
    assert screen_jd(ads, [], p) == ([], 0)


def test_quick_score_block_spaced_title(monkeypatch):
    monkeypatch.setattr(
        'app.services.matching_service.embed_many',
        lambda texts: {t: [1.0, 0.0] for t in texts}
    )
    analysis = SimpleNamespace(skills=['Python'], recommended_positions=['AI销售助理'])
    # 「获客」「操作员」：标题带运营类词就不拦，不带照样拦
    # 「BD」是商务拓展，本质是销售
    names = ['AI 软 件 销 售 助 理', 'AI招商助理', '跨境电商AI操作员', '独立站SEO运营+AI获客', 'AI获客专员', '本地生活BD']
    jobs = [QuickJob(name=n, tags=[]) for n in names]
    assert [item.score for item in quick_score(analysis, jobs)] == [0, 0, 70, 70, 0, 0]


def test_salary_cut_only_once(monkeypatch):
    monkeypatch.setattr('app.services.matching_service.embed_many', lambda texts: {t: [1.0, 0.0] for t in texts})
    analysis = SimpleNamespace(skills=[], recommended_positions=[])
    targets = load_targets([{'name': 'B', 'positions': ['电商运营'], 'max_years': 3, 'min_pay': 7}], analysis)
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 2.75}
    jobs = [SimpleNamespace(name='电商运营助理', tags=[], jd='负责店铺日常运营', salary=s) for s in ('8-12K', '6-8K')]
    # 工资下限不到 7K、上限够 7K：只扣 5 分，不是 10 分
    assert [b['score'] for b in score_jobs(analysis, targets, jobs, p)] == [70, 65]
    # 读过 JD 的 4-7K 也是 0 分
    low = [SimpleNamespace(name='电商运营助理', tags=[], jd='负责店铺日常运营，接受无经验', salary='4-7K')]
    assert score_jobs(analysis, targets, low, p)[0]['score'] == 0


def test_manager_title_and_big_case(monkeypatch):
    monkeypatch.setattr('app.services.matching_service.embed_many', lambda texts: {t: [1.0, 0.0] for t in texts})
    analysis = SimpleNamespace(skills=[], recommended_positions=[])
    t = SimpleNamespace(name='B', positions=['电商运营'], junior=[], max_years=3, min_pay=7, good_words=[])
    names = ['电商运营主管', '项目经理（AI方向）', 'Facebook广告投放主管/专员', '经理助理']
    scores = [i.score for i in quick_score(analysis, [QuickJob(name=n, tags=[]) for n in names], target=t)]
    # 主管 / 经理直接 0 分；标题同时写了专员、助理的不拦
    assert scores[0] == 0 and scores[1] == 0 and scores[2] > 0 and scores[3] > 0
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 3.0}
    assert screen_jd('3、具备单店年销破千万的成功操盘案例', [], p)[0] == ['要百万级操盘案例']
    # 公司介绍里的营收规模不算
    assert screen_jd('公司年营收过亿，团队氛围好', [], p)[0] == []


def test_business_hits_and_salary_screen():
    assert business_hits('负责ERP系统对接、Excel报表和ROI数据分析') == [
        'ERP','Excel','数据分析','ROI','报表','系统对接'
    ]
    target=SimpleNamespace(min_pay=7)
    # 工资最高不超过 7K 直接不打分（4-7K 也算）；跨过 7K 只轻扣 5 分。
    assert screen_pay('5-6K',target) == (['薪资上限不超过7K'],0)
    assert screen_pay('4-7K',target) == (['薪资上限不超过7K'],0)
    assert screen_pay('6-10K',target) == (['薪资下限低于7K'],5)
    assert screen_pay('7-10K',target) == ([],0)
    assert screen_pay('面议',target) == ([],0)
    assert decode_pay('\ue037-\ue039K') == '6-8K'
    assert parse_pay_range('\ue037-\ue039K') == (6.0,8.0)


def test_requirement_hits_count_distinct_groups_once():
    hits,points=requirement_hits(
        '使用 Python、FastAPI、Flask，操作 MySQL、SQLAlchemy 和 ORM；'
        '开发 REST API，建设 RAG 知识库与 Agent Tool Calling。'
    )
    assert hits == [
        'Python','Web框架','SQL/数据库','API/接口','RAG/知识库','Agent/工具调用'
    ]
    # FastAPI/Flask、MySQL/SQLAlchemy/ORM 都各自属于一个能力项，不重复堆分。
    assert points == 12


def test_cross_border_requirement_is_exposed_without_double_score():
    hits, points = requirement_hits('要求1年以上Amazon跨境电商运营经验')

    assert '跨境电商经验' in hits
    assert '电商平台/运营' in hits
    assert points == 2


def test_inventory_requirement_is_exposed_without_double_score():
    hits, points = requirement_hits('使用Pandas处理订单、库存和毛利数据')

    assert '库存/仓储经验' in hits
    assert '商品/订单/库存' in hits
    assert points == 2


def test_more_matching_requirements_get_higher_score():
    p={'edu':3,'full':3,'elite':False,'years':2.0}
    few=screen_jd('负责 Python 脚本开发',[],p)[1]
    many=screen_jd(
        '使用 Python、FastAPI、MySQL 开发 API，接入大模型并建设 RAG 知识库',[],p
    )[1]
    assert apply_jd(70,[],many) > apply_jd(70,[],few)
    assert requirement_hits('经验不限，可接受个人项目和项目经验即可')[1] == 9


def test_advanced_requirements_are_hard_flags():
    p={'edu':3,'full':3,'elite':False,'years':2.0}
    flags,_=screen_jd(
        '负责大模型预训练和 CUDA 高性能推理，独立负责千万级核心项目',[],p
    )
    assert flags == ['偏算法/模型训练','需独立负责大型项目']
    assert apply_jd(95,flags,0) == 50


def test_experience_text_uses_minimum_not_upper_bound():
    p={'edu':3,'full':3,'elite':False,'years':2.75}
    target=SimpleNamespace(max_years=3,good_words=[])
    assert screen_jd('工作经验至少3年',[],p,'ERP实施助理',target)[0] == ['要3年经验']
    assert screen_jd('3年以下工作经验',[],p,'ERP实施助理',target)[0] == []
    assert screen_jd('工作经验2年',[],p,'ERP实施助理',target)[0] == []
    assert screen_jd('3年以上游戏投放经验',[],p,'广告投放助理',target)[0] == ['要3年游戏经验']


def test_configured_title_rules_block_semantic_false_positives():
    positions=['AI应用助理','ERP实施助理','跨境电商运营助理','广告投放助理']
    assert title_rule_match('AI应用工程师（跨境电商方向）',positions) is True
    assert title_rule_match('金蝶ERP实施顾问',positions) is True
    assert title_rule_match('TikTok跨境电商运营助理',positions) is True
    assert title_rule_match('信息流投放助理',positions) is True
    # 没写助理 / 专员也算对上电商运营、广告投放方向
    assert title_rule_match('facebook广告投放',positions) is True
    assert title_rule_match('国内电商运营',['电商运营助理']) is True
    assert title_rule_match('抖音电商运营',['电商运营助理']) is True
    assert title_rule_match('电商客服',['电商运营助理']) is False
    # 平台名也算电商运营；不带「助理」的两个方向规则一样
    for title in ('京东运营', '天猫运营', '抖店运营', '拼多多运营专员', '淘宝店铺运营'):
        assert title_rule_match(title,['电商运营']) is True
    assert title_rule_match('天猫客服',['电商运营']) is False
    assert title_rule_match('facebook广告投放',['广告投放']) is True
    assert title_rule_match('AI产品经理（数据中台方向）',positions) is False
    assert title_rule_match('服装设计助理（AI辅助）',positions) is False
    assert title_rule_match('短视频剪辑师',positions) is False
    assert title_rule_match('任意岗位',['自定义方向']) is None


def test_screen_jd_field_and_bonus():
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 3.0}
    field = '负责设备安装与故障维修\n熟练使用 Python'
    flags, cut = screen_jd(field, [], p)
    assert flags == ['偏硬件/现场']
    assert cut == -2
    assert apply_jd(80, flags, cut) == 50

    # 技术支持类标题：JD 里硬件词明显多就是硬件支持；同样的 JD 放在运营岗不算
    hw = '负责客户现场安装调试，需驻厂，熟悉传感器和PLC'
    assert screen_jd(hw, [], p, '技术支持工程师')[0] == ['偏硬件/现场']
    assert screen_jd(hw, [], p, '电商运营')[0] == []
    assert screen_jd('负责SaaS系统部署和客户培训，定期设备巡检', [], p, '技术支持工程师')[0] == []

    # DeepSeek、Python、电商运营是三个不同能力项。
    good = '熟练使用 DeepSeek 写 Python 脚本\n负责抖音本地生活商家的团购运营'
    flags, cut = screen_jd(good, [], p)
    # 「使用 DeepSeek」是 AI 提效信号，再加 10 分
    assert (flags, cut) == ([], -16)
    assert apply_jd(70, flags, cut) == 86
    assert apply_jd(95, flags, cut) == 100
    assert apply_jd(0, flags, cut) == 0


def test_screen_jd_things_i_cant_meet():
    p = {'edu': 3, 'full': 2, 'elite': False, 'years': 2.75}
    t = SimpleNamespace(max_years=3, min_pay=7, good_words=[])
    jd = ('1、2026届全日制统招本科及以上学历，计算机相关专业优先\n'
          '2、2年以上亚马逊欧美站广告投放经验\n'
          '3、英语可作为工作语言\n'
          '4、1年以上抖音运营经验')
    flags, _ = screen_jd(jd, [], p, '亚马逊广告运营', t)
    # 「优先」只管后半句；亚马逊没做过，要 2 年不行；抖音做过，要 1 年没问题
    assert flags == ['要全日制本科', '只招应届', '要外语/粤语', '要2年亚马逊经验']
    assert apply_jd(70, flags, -10) == 50
    # 没做过的领域：要 2 年及以上压到 50；只要 1 年或半年的标出来扣 10 分，不拦
    assert screen_jd('两年及以上Google和Meta广告实操经验', [], p, '广告投放专员', t)[0] == ['要2年广告经验']
    # 要 1 年经验不再扣分，只剩广告投放能力项加 2 分
    assert screen_jd('1年以上广告投放经验', [], p, '广告投放专员', t) == (['需1年广告经验'], -2)
    assert screen_jd('半年以上FB广告投放经验', [], p, '广告投放专员', t)[0] == ['需半年广告经验']
    # 同一行写了应届生也可接受，不扣
    assert screen_jd('1年以上AI应用经验;优秀应届生也可接受', [], p, 'AI助理', t)[0] == []
    # 「其中之一」不算可选
    assert screen_jd('2 年及以上 Shopee、Lazada 其中之一运营经验', [], p, '跨境电商运营', t)[0] == ['要2年Shopee经验']
    # 「暂无2026届招聘需求」是不招应届，不算只招应届
    assert screen_jd('暂无2026届应届生招聘需求', [], p, '运营助理', t)[0] == []
    # 「3–5 年」用的是长横线，前面还有「-」列表符号
    assert screen_jd('-3–5 年海外社媒运营经验', [], p, '运营助理', t)[0] == ['要3年海外经验']
    # 标签「1-3年」+ 标题是没做过的领域：JD 没写年限、没说接受新人才扣分
    assert screen_jd('负责店铺日常运营', ['1-3年'], p, '亚马逊运营助理', t)[0] == ['需1年亚马逊经验']
    assert screen_jd('负责店铺日常运营，接受无亚马逊运营经验', ['1-3年'], p, '亚马逊运营助理', t)[0] == []
    assert screen_jd('1-2年跨境电商数据分析经验优先', ['1-3年'], p, '跨境电商数据分析师', t)[0] == []
    assert screen_jd('负责门店团购上架', ['1-3年'], p, '抖音本地生活运营', t)[0] == []


def test_quick_score_low_pay_is_capped(monkeypatch):
    monkeypatch.setattr('app.services.matching_service.embed_many', lambda texts: {t: [1.0, 0.0] for t in texts})
    analysis = SimpleNamespace(skills=[], recommended_positions=[])
    t = SimpleNamespace(name='B', positions=['电商运营'], junior=[], max_years=3, min_pay=7, good_words=[])
    jobs = [QuickJob(name='电商运营助理', tags=[], salary=s) for s in ('8-12K', '6-8K', '面议', '4-7K')]
    # 6-8K 跨过期望值，只轻扣 5 分；4-7K 最高不超过 7K，直接 0 分、不读 JD
    items = quick_score(analysis, jobs, target=t)
    assert [i.score for i in items] == [70, 65, 70, 0]
    assert (items[3].read_jd, items[3].screen, items[3].reason) == (False, 'skip', '薪资上限不超过7K')


def test_title_wording_miss_keeps_partial_score(monkeypatch):
    monkeypatch.setattr('app.services.matching_service.embed_many', lambda texts: {t: [1.0, 0.0] for t in texts})
    analysis = SimpleNamespace(skills=[], recommended_positions=[])
    t = SimpleNamespace(name='B', positions=['广告投放助理'], junior=[], max_years=3, min_pay=7, good_words=[])
    # 「推广助理」没写投放：标题写法不完全匹配，压到 55；「投放助理」算投放方向
    jobs = [QuickJob(name=n, tags=['经验不限'], salary='8-13K') for n in ('推广助理（可接受应届生）', '投放助理（可接受应届生）')]
    assert [i.score for i in quick_score(analysis, jobs, target=t)] == [55, 70]


def test_exact_target_title_and_under_three_years_are_kept(monkeypatch):
    monkeypatch.setattr('app.services.matching_service.embed_many', lambda texts: {t: [0.0, 0.0] for t in texts})
    analysis = SimpleNamespace(skills=[], recommended_positions=[])
    t = SimpleNamespace(name='B', positions=['广告投放助理'], junior=[], max_years=3, min_pay=7, good_words=[])
    jobs = [
        QuickJob(name='广告投放专员', tags=['1-3年'], salary='8-13K'),
        QuickJob(name='广告投放专员', tags=['3-5年'], salary='8-13K'),
        QuickJob(name='短视频剪辑师', tags=['经验不限'], salary='8-13K'),
    ]
    result = quick_score(analysis, jobs, target=t)
    # 标题不再给保底分：方向对上也只是优先读 JD，分数等 JD 来给
    assert [item.score for item in result] == [20, 0, 0]
    assert [item.read_jd for item in result] == [True, False, False]
    assert [item.screen for item in result] == ['priority', 'skip', 'skip']


def test_team_lead_title_is_skipped_before_jd(monkeypatch):
    monkeypatch.setattr('app.services.matching_service.embed_many', lambda texts: {t: [1.0, 0.0] for t in texts})
    analysis = SimpleNamespace(skills=[], recommended_positions=[])
    t = SimpleNamespace(name='B', positions=['广告投放助理'], junior=[], max_years=3, min_pay=7, good_words=[])
    item = quick_score(analysis, [QuickJob(name='广告投放/组长', tags=['经验不限'], salary='15-30K')], target=t)[0]
    assert (item.score, item.read_jd, item.screen) == (0, False, 'skip')
    assert item.reason == '标题含排除词「组长」'


def test_manager_or_supervisor_title_is_reviewed_not_skipped(monkeypatch):
    monkeypatch.setattr('app.services.matching_service.embed_many', lambda texts: {t: [0.0, 0.0] for t in texts})
    analysis = SimpleNamespace(skills=[], recommended_positions=[])
    t = SimpleNamespace(name='B', positions=['SaaS实施助理'], junior=[], max_years=3, min_pay=7, good_words=[])
    jobs = [
        QuickJob(name='SaaS项目经理助理', tags=['经验不限'], salary='8-12K'),
        QuickJob(name='数字化主管助理', tags=['经验不限'], salary='8-12K'),
    ]
    result = quick_score(analysis, jobs, target=t)
    assert [item.read_jd for item in result] == [True, True]
    assert [item.screen for item in result] == ['priority', 'review']


def test_unrelated_development_title_is_skipped(monkeypatch):
    monkeypatch.setattr('app.services.matching_service.embed_many', lambda texts: {t: [1.0, 0.0] for t in texts})
    analysis = SimpleNamespace(skills=[], recommended_positions=[])
    t = SimpleNamespace(name='B', positions=['Python自动化', 'ERP实施助理'], junior=[], max_years=3, min_pay=7, good_words=[])
    jobs = [
        QuickJob(name='MES开发工程师', tags=['经验不限'], salary='10-15K'),
        QuickJob(name='Python自动化开发工程师', tags=['经验不限'], salary='10-15K'),
    ]
    result = quick_score(analysis, jobs, target=t)
    assert [item.read_jd for item in result] == [False, True]
    assert result[0].reason == '开发方向明显不符'


def test_local_life_and_ad_assistant_titles():
    positions = ['商家运营', '本地生活运营', '广告投放助理']
    assert title_rule_match('美团运营专员', positions) is True
    assert title_rule_match('本地生活运营（连锁门店）', positions) is True
    assert title_rule_match('淘宝闪购-外卖商家运营', positions) is True
    assert title_rule_match('短剧投放助理（招应届生）', positions) is True
    assert title_rule_match('美团推广专员', positions) is False


def test_software_dev_direction_and_language():
    positions = ['软件开发']
    assert title_rule_match('Python开发工程师（初级）', positions) is True
    assert title_rule_match('SaaS开发工程师（Vue3+Python 全栈）', positions) is True
    assert title_rule_match('RPA程序员', positions) is True
    # 产品开发是选品；算法、架构师不算这个方向
    assert title_rule_match('产品开发助理（跨境电商）', positions) is False
    assert title_rule_match('算法工程师', positions) is False
    assert title_rule_match('AI产品开发助理', ['AI开发助理']) is False
    p = {'edu': 3, 'full': 2, 'elite': False, 'years': 2.75, 'age': 26}
    t = SimpleNamespace(max_years=3, min_pay=7, good_words=[])
    # 开发岗 JD 用 Go / Java、没提 Python 或 JS：压到 50；提了 Python、或者标题写了 Python 的不算；不是开发岗的不管
    assert '开发语言不是Python/JS' in screen_jd('熟悉Go语言，负责微服务开发', [], p, 'Golang后端（Agent方向）', t)[0]
    assert '开发语言不是Python/JS' in screen_jd('熟练使用Java、Spring', [], p, '后端开发工程师', t)[0]
    assert '开发语言不是Python/JS' not in screen_jd('熟悉Java或Python', [], p, '后端开发工程师', t)[0]
    assert '开发语言不是Python/JS' not in screen_jd('会C++', [], p, 'Python/C++ 软件开发工程师', t)[0]
    assert '开发语言不是Python/JS' not in screen_jd('熟悉Google广告后台', [], p, '前端开发工程师', t)[0]
    assert '开发语言不是Python/JS' not in screen_jd('了解Java系统对接', [], p, '软件实施工程师', t)[0]
    # 标题写明 C++、JD 只在加分项里提一句 Python：照样算语言不对
    jd = '使用 C++/Qt 开发桌面客户端' + chr(10) + '加分项' + chr(10) + 'C++ 接 Python 脚本'
    assert '开发语言不是Python/JS' in screen_jd(jd, [], p, 'C++ 客户端开发工程师（AI Coding）', t)[0]
    assert '开发语言不是Python/JS' in screen_jd(jd, [], p, '客户端开发工程师', t)[0]
    assert '开发语言不是Python/JS' not in screen_jd('使用 C++/Qt 开发' + chr(10) + '熟悉 Python', [], p, '客户端开发工程师', t)[0]


def test_short_keywords_need_word_boundary():
    # 「Electron」里的 ctr、「Android」里的 roi 不算广告指标；「项目上线」不算部署
    hits, _ = requirement_hits('跨平台 Electron 混合桌面；Android 客户端；至少一个项目上线')
    assert '广告投放/数据指标' not in hits and 'Docker/Linux部署' not in hits
    hits, _ = requirement_hits('关注 CTR、ROI 等投放数据；负责 Linux 服务部署')
    assert '广告投放/数据指标' in hits and 'Docker/Linux部署' in hits


def test_product_dev_and_boss_assistant_titles_not_blocked(monkeypatch):
    monkeypatch.setattr('app.services.matching_service.embed_many', lambda texts: {t: [1.0, 0.0] for t in texts})
    analysis = SimpleNamespace(skills=[], recommended_positions=[])
    t = SimpleNamespace(name='B', positions=['电商运营助理'], junior=[], max_years=3, min_pay=7, good_words=[])
    names = ['产品开发助理/专员（跨境电商-家具）', '电商总监助理', '电商运营总监', '软件开发工程师']
    scores = [i.score for i in quick_score(analysis, [QuickJob(name=n, tags=[]) for n in names], target=t)]
    # 产品开发是选品，总监助理是助理岗；真正的总监、写代码的开发岗照样 0 分
    assert scores[0] > 0 and scores[1] > 0 and scores[2] == 0 and scores[3] == 0


def test_screen_jd_service_new_hand_solo_and_age():
    p = {'edu': 3, 'full': 2, 'elite': False, 'years': 2.75, 'age': 26}
    t = SimpleNamespace(max_years=3, min_pay=7, good_words=[])
    # 客服 / 中控：标题写明、JD 要客服中控经验、主要做客服、要打字速度
    assert screen_jd('协助运营', [], p, '电商运营助理/客服（综合方向）', t)[0] == ['偏客服/中控']
    assert screen_jd('1.有抖音中控经验，熟悉后台操作', [], p, '国内电商运营助理', t)[0] == ['偏客服/中控']
    assert screen_jd('协助直播事务，处理客服工作', [], p, '电商运营助理', t)[0] == ['偏客服/中控']
    assert screen_jd('电脑操作熟练，打字速度不低于50字/分钟', [], p, '电商运营助理', t)[0] == ['偏客服/中控']
    # 「优先」「可接受」不算；AI 客服系统类岗位不算
    assert screen_jd('有电商平台客服经验优先', [], p, '电商运营助理', t)[0] == []
    assert screen_jd('加分项：了解订单流程；熟悉平台规则、有客服经验', [], p, '电商运营助理', t)[0] == []
    assert screen_jd('可接受有经验的应届生及有售前售后客服经验', [], p, '电商运营助理', t)[0] == []
    assert screen_jd('负责智能客服知识库搭建', [], p, 'AI客服实施助理', t)[0] == []
    # 不收新手：没做过的领域才算，本地生活是我做过的
    assert screen_jd('淘宝天猫运营（不支持小白）', [], p, '淘宝天猫京东运营', t)[0] == ['不收新手']
    assert screen_jd('不接受无经验牛人\n负责门店团购上架', [], p, '网络运营', t)[0] == []
    # 独立运营：要求里写的算；以后才独立的、写了优先的、本地生活的不算
    assert screen_jd('2.1-3年独立运营，有从0到1起店案例', [], p, '抖音运营助理', t)[0] == ['要独立运营经验']
    assert screen_jd('1-3个月系统学习后可以独立运营店铺', [], p, '电商运营助理', t)[0] == []
    assert screen_jd('优秀者可独立负责平台店铺全盘运营', [], p, '电商运营助理', t)[0] == []
    assert screen_jd('有独立操盘实体门店线上账号经验优先', [], p, '电商运营助理', t)[0] == []
    assert screen_jd('能独立完成店铺整体运营和广告投放', [], p, '美团推广/商家运营', t)[0] == []
    # 年龄：26 岁，18-25 岁不行；18-26 岁、32 周岁及以下可以；简历没写年龄不判断
    assert screen_jd('4、18-25岁', [], p, '电商运营助理', t)[0] == ['超出年龄要求']
    assert screen_jd('1、18-26岁，有相关工作经验优先考虑', [], p, '电商运营助理', t)[0] == []
    assert screen_jd('大专及以上学历，年龄 32 周岁及以下', [], p, '商家运营专员', t)[0] == []
    assert screen_jd('28周岁以下，本科及以上', [], {**p, 'age': 30}, '流量运营', t)[0] == ['超出年龄要求']
    assert screen_jd('4、18-25岁', [], {**p, 'age': None}, '电商运营助理', t)[0] == []
    # 「1年以上相关经验」没点名领域：看标题
    assert screen_jd('本科及以上学历；1年以上相关经验', [], p, '亚马逊运营专员（精品/精铺）', t)[0] == ['需1年亚马逊经验']


def test_sales_check_local_push_and_merchant_bd():
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 3.0}
    # 「抖音本地推」是投放工具，「接受无商家拓展经验」是 BOSS 标签，都不算销售
    local = '接受无商家拓展经验\n执行抖音本地推、美团推广通付费投放\n底薪 + 基础业绩提成'
    assert screen_jd(local, [], p, '商家运营专员')[0] == []
    # 「引流获客」是用团购活动拉用户，不是跑业务
    assert screen_jd('引流获客：通过团购活动策划引导用户购买体验课\n底薪+提成', [], p, '本地生活运营（美团/抖音团购）')[0] == []
    # 拓展新商户、达成业绩目标：是销售
    bd = '负责区域内新商户的拓展、老商户的维护，达成业绩目标'
    assert screen_jd(bd, [], p, '美团外卖商家拓展运营专员')[0] == ['疑似销售岗']


def test_boss_radical_characters_read_as_normal_text(monkeypatch):
    assert plain_text('英语⽆要求，⼯作经验，⻢上⻅⾯') == '英语无要求，工作经验，马上见面'
    assert plain_text(None) is None
    monkeypatch.setattr('app.services.matching_service.embed_many', lambda texts: {t: [1.0, 0.0] for t in texts})
    analysis = SimpleNamespace(skills=[], recommended_positions=[])
    targets = load_targets([{'name': 'B', 'positions': ['亚马逊运营助理'], 'max_years': 3, 'min_pay': 7}], analysis)
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 2.75}
    jobs = [SimpleNamespace(name='amazon运营助理', tags=[], jd='负责listing优化\n英语⽆要求', salary='8-12K')]
    # 「英语⽆要求」换回「英语无要求」，不算要外语
    assert score_jobs(analysis, targets, jobs, p)[0]['flags'] == []


def test_design_editing_jd_and_merchant_field():
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 2.75}
    t = SimpleNamespace(max_years=3, min_pay=7, good_words=[])
    # 主要做剪辑 / 作图：要求熟练剪映、作图软件，或者独立完成图片设计、海报排版
    assert screen_jd('1.熟练运用剪映剪辑短视频爆点钩子卖点视频', [], p, '电商运营助理', t)[0] == ['偏剪辑/设计']
    assert screen_jd('能独立完成符合要求的图片设计，熟悉小红书', [], p, '电商运营助理', t)[0] == ['偏剪辑/设计']
    assert screen_jd('会使用PS等设计工具，能够独立完成产品图片排版、海报制作等图文工作', [], p, '国内电商运营助理', t)[0] == ['偏剪辑/设计']
    # 有点 PS 基础、写了优先、配合美工、独立完成方案设计都不算
    assert screen_jd('具备一定的PS功底和审美能力', [], p, '电商运营专员', t)[0] == []
    assert screen_jd('熟练使用PS者优先', [], p, '电商运营助理', t)[0] == []
    assert screen_jd('配合美工完成主图、详情页优化', [], p, '电商运营助理', t)[0] == []
    assert screen_jd('能独立完成客户需求分析和方案设计', [], p, 'AI实施助理', t)[0] == []
    # 「商家运营」不代表是我做过的本地生活：阿里国际站的商家运营按没做过的领域算
    assert screen_jd('负责店铺日常运营', ['1-3年'], p, '阿里巴巴国际站运营 商家运营', t)[0] == ['需1年阿里巴巴国际站经验']
    assert screen_jd('负责门店团购上架', ['1-3年'], p, '商家运营专员', t)[0] == []


def test_douyin_ecommerce_is_not_my_field():
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 2.75}
    t = SimpleNamespace(max_years=3, min_pay=7, good_words=[])
    # 我做的是抖音本地生活：抖音电商、抖店要 2 年压到 50，要 1 年扣 10
    assert screen_jd('2年以上抖音电商运营经验', [], p, '电商运营助理', t)[0] == ['要2年电商经验']
    assert screen_jd('1年以上抖店运营经验', [], p, '运营助理', t)[0] == ['需1年抖店经验']
    assert screen_jd('负责店铺日常运营', ['1-3年'], p, '抖音电商运营', t)[0] == ['需1年电商经验']
    # 只写「抖音运营」没点名领域、抖音本地生活：照常
    assert screen_jd('2年以上抖音运营经验', [], p, '运营助理', t)[0] == []
    assert screen_jd('2年以上抖音本地生活运营经验', [], p, '抖音团购运营', t)[0] == []


def test_team_lead_and_architecture_requirements():
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 2.75}
    t = SimpleNamespace(max_years=3, min_pay=7, good_words=[])
    # JD 正文要求带团队、主导架构设计：压到 50
    jd = ('团队管理经验\n架构设计经验\n1、主导AI技术架构设计、迭代与性能优化\n'
          '2、具备团队管理能力，能够带领3-5人小团队快速交付MVP')
    assert screen_jd(jd, [], p, 'ai应用开发工程师', t)[0] == ['要带团队', '要主导架构设计']
    assert screen_jd('3、带领3-6人运营小组，组织周度复盘', [], p, '亚马逊运营', t)[0] == ['要带团队']
    # 只有 BOSS 标签、整行写了优先、以后表现优秀才带团队、管理 1 人、搭建团队知识库：都不算
    assert screen_jd('团队管理经验\n架构设计经验\n负责店铺日常运营', [], p, '抖音运营助理', t)[0] == []
    assert screen_jd('打造爆款者优先考虑。（具备团队管理经验者，薪资可面议）', [], p, '亚马逊运营', t)[0] == []
    assert screen_jd('表现优秀者或有团队管理经验者可定位为运营主管', [], p, '亚马逊广告专员', t)[0] == []
    assert screen_jd('参与搭建团队内部知识库；行政管理1人', [], p, '研发项目助理', t)[0] == []


def test_graduate_jobs_and_one_year_ease():
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 2.75}
    t = SimpleNamespace(max_years=3, min_pay=7, good_words=[])
    # 写了届别、校招、「学历…应届毕业生」：只招应届，压到 50
    assert screen_jd('27届本科\n负责店铺日常运营', [], p, '电商运营助理', t)[0] == ['只招应届']
    assert screen_jd('岗位职责】-26年/27年毕业', [], p, 'ai工程师', t)[0] == ['只招应届']
    assert screen_jd('校招储备岗', [], p, '电商运营助理', t)[0] == ['只招应届']
    assert screen_jd('1. 学历要求：本科及以上学历，应届毕业生。', [], p, '院长助理', t)[0] == ['只招应届']
    assert screen_jd('负责店铺日常运营', [], p, '国内电商运营助理【27届】', t)[0] == ['只招应届']
    # 届别写了亦可 / 优先、应届毕业生优先：扣 10 分
    assert screen_jd('（4）26届/27届毕业生亦可。', [], p, '跨境电商运营助理', t) == (['面向应届生'], 10)
    assert screen_jd('4、大专以上，应届毕业生优先。', [], p, '电商运营专员', t) == (['面向应届生'], 10)
    # 只写接受应届生、暂无应届需求、第26届广交会：不扣
    assert screen_jd('有无经验均可，接受应届生、转行求职者', [], p, '电商运营助理', t)[0] == []
    assert screen_jd('暂无2026届应届生招聘需求', [], p, '运营助理', t)[0] == []
    assert screen_jd('公司连续参加第26届广交会', [], p, '跨境电商运营助理', t)[0] == []
    # 没做过的领域要 1 年：标题对上求职方向扣 5；再加上 JD 能力项 ≥8 分就不扣
    tt = SimpleNamespace(positions=['TikTok运营助理'], junior=[], max_years=3, min_pay=7, good_words=[])
    assert screen_jd('1年以上TikTok运营经验', [], p, 'TikTok运营专员', tt) == (['需1年TikTok经验'], -2)
    # JD 技术词再多也不放宽，只有方向对口才少扣 5
    many = '1年以上TikTok运营经验\n负责数据分析、商品上架、订单和库存管理，广告投放ROI优化，使用Excel'
    assert screen_jd(many, [], p, 'TikTok运营专员', tt) == (['需1年TikTok经验'], -8)


def test_ai_and_data_title_directions():
    positions = ['AI运营助理', 'Agent应用开发', 'AI开发助理', 'AI技术支持', '数字化实施', '电商自动化', '电商数据专员']
    assert title_rule_match('AI运营助理+五险一金——小白可入', positions) is True
    assert title_rule_match('电商AI Agent开发工程师（服装电商方向）', positions) is True
    assert title_rule_match('ai开发工程师助理', positions) is True
    assert title_rule_match('AI技术支持/客户成功', positions) is True
    assert title_rule_match('OA实施工程师', positions) is True
    assert title_rule_match('自动化工程师（亚马逊）', positions) is True
    assert title_rule_match('电商数据专员（五险一金）', positions) is True
    # 机器人 AI 工程师、工业自动化不算
    assert title_rule_match('仿生机器人运控Ai工程师', positions) is False
    assert title_rule_match('自动化控制工程师', positions) is False


def test_video_script_solo_store_and_platform_any():
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 2.75}
    t = SimpleNamespace(max_years=3, min_pay=7, good_words=[])
    # 直播 / 短视频方向写「脚本」是视频脚本，不算会用自动化工具
    assert screen_jd('负责短视频脚本策划和直播间运营', [], p, '国内电商运营助理（短视频/直播方向）', t)[0] == ['内容岗没要求AI工具']
    assert screen_jd('会写Python脚本处理直播数据', [], p, '直播运营助理', t)[0] == []
    # 能够独立操作店铺并担任店长：要独立运营；能独立操作店铺后台：不算
    assert screen_jd('1、具备1年以上店铺运营经验，能够独立操作店铺，并能担任店长', [], p, '电商运营', t)[0] == ['要独立运营经验']
    assert screen_jd('协助负责京东店铺日常维护，能独立操作店铺后台', [], p, '电商运营专员/助理', t)[0] == []
    # 「跨境平台不限」只是平台随意，1-3 年跨境经验照样要
    assert screen_jd('1-3 年跨境电商精品/品牌运营经验（跨境平台不限，类目不限）', [], p, '跨境电商独立站品牌运营', t)[0] == ['需1年跨境经验']


def test_no_experience_wording_is_a_bonus_word():
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 2.75}
    t = SimpleNamespace(max_years=3, min_pay=7, good_words=['经验不限'])
    # 「可无经验」「接受无经验」和「经验不限」一样算加分词
    assert screen_jd('可无经验', [], p, '跨境电商运营', t) == ([], -5)
    assert screen_jd('接受无经验，有人带', [], p, '跨境电商运营', t)[1] <= -5


def test_pay_floor_and_deep_requirements():
    target = SimpleNamespace(min_pay=7)
    # 下限比期望低 1K 以上直接排除；6～7K 之间扣 5 分；7-7K 下限达标放行
    assert screen_pay('5-15K', target) == (['薪资下限不到6K'], 0)
    assert screen_pay('6-10K', target) == (['薪资下限低于7K'], 5)
    assert screen_pay('7-7K', target) == ([], 0)
    # 6-7K 最高也就 7K，和 4-7K 一样排除
    assert screen_pay('6-7K', target) == (['薪资上限不超过7K'], 0)
    assert screen_pay('5-6K', target) == (['薪资上限不超过7K'], 0)
    # 「精通Python、独立负责架构」不再加分；「了解Python」照常加
    assert requirement_hits('了解Python即可')[1] == 2
    assert requirement_hits('精通Python，独立负责架构设计')[1] == 0
    assert requirement_hits('熟悉Python脚本；精通Java')[1] == 2


def test_training_and_certificate_wording():
    # 「负责客户培训」是你去培训别人，不算公司培养你
    assert good_hits(['提供培训'], '负责客户培训与上线支持') == set()
    assert good_hits(['提供培训'], '公司提供系统培训和带教') == {'提供培训'}
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 2.75}
    t = SimpleNamespace(max_years=3, min_pay=7, good_words=[])
    # 「熟悉SSL证书配置」是技术活，不算要资格证
    assert screen_jd('需熟悉SSL证书部署与配置', [], p, '技术支持', t)[0] == []
    assert screen_jd('须持有电子商务师证书', [], p, '电商运营助理', t)[0] == ['要证书']


def test_backup_direction_costs_five(monkeypatch):
    monkeypatch.setattr('app.services.matching_service.embed_many', lambda texts: {t: [1.0, 0.0] for t in texts})
    analysis = SimpleNamespace(skills=[], recommended_positions=[])
    t = SimpleNamespace(name='B', positions=['电商运营助理', 'ERP实施助理'], junior=[], backup=['ERP实施助理'],
                        max_years=3, min_pay=7, good_words=[])
    jobs = [QuickJob(name='ERP实施顾问', tags=[], salary='8-12K'), QuickJob(name='电商运营助理', tags=[], salary='8-12K')]
    scores = [i.score for i in quick_score(analysis, jobs, target=t)]
    # 只对上备选方向的扣 5 分，对上主投方向的不扣
    assert scores[0] == scores[1] - 5


def test_mentoring_jobs_get_sixty(monkeypatch):
    names = {'运营专员': [0.6, 0.8], 'PMC计划员': [0.3, 0.95]}
    monkeypatch.setattr('app.services.matching_service.embed_many', lambda texts: {t: names.get(t, [1.0, 0.0]) for t in texts})
    analysis = SimpleNamespace(skills=[], recommended_positions=[])
    targets = load_targets([{'name': 'B', 'positions': ['电商运营'], 'max_years': 3, 'min_pay': 7}], analysis)
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 2.75}

    def score(jd, title='运营专员'):
        job = SimpleNamespace(name=title, tags=[], jd=jd, salary='8-12K')
        return score_jobs(analysis, targets, [job], p)[0]

    # 进公司有人带教（有人带、导师一对一、带薪培训、重点培养、专人带），没踩硬门槛：至少 60 分
    got = score('协同开发工作，有人带')
    assert got['score'] == 60 and '有人带/可培养' in got['hits']
    for jd in ('入职安排导师一对一指导', '提供带薪培训', '公司重点培养', '专人带你上手'):
        assert score(jd)['score'] == 60, jd
    # 是你去带新人、去培训客户、踩了硬门槛、标题完全不沾边：不保底
    assert score('负责新人带教工作')['score'] < 60
    assert score('担任讲师，给学员上课')['score'] < 60
    assert score('须持有电子商务师证书，入职有人带')['score'] <= 50
    assert score('入职有人带', 'PMC计划员')['score'] < 60
    # 只要 1 年亚马逊经验、又不扣分：算合适，也能保底 60（用户：一年或一年内都可以）
    got = score('1年以上亚马逊运营经验' + chr(10) + '入职有人带')
    assert got['score'] == 60 and '只要1年亚马逊经验' in got['pros']
    assert not any(c.startswith('需1年') for c in got['cons'])
    # 工资下限≥15K 的高薪岗照旧扣分，算不合适，不保底
    job = SimpleNamespace(name='运营专员', tags=[], jd='1年以上亚马逊运营经验' + chr(10) + '入职有人带', salary='20-30K')
    got = score_jobs(analysis, targets, [job], p)[0]
    assert got['score'] < 60 and any(c.startswith('需1年亚马逊经验（-') for c in got['cons'])


def test_sales_piece_pay_and_equipment_debug():
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 2.75}
    t = SimpleNamespace(max_years=3, min_pay=7, good_words=[])
    # 广告销售、To B 销售、商家开拓、洽谈签约：算销售
    assert screen_jd('广告销售经验', [], p, '商家广告入驻', t)[0] == ['疑似销售岗']
    assert screen_jd('负责本地商家的开拓、运营维护工作，促进商家签约数的提升', [], p, 'TO B 开拓运营专员', t)[0] == ['疑似销售岗']
    # 写了优先、本地生活的门店入驻：不算
    assert screen_jd('有广告销售经验者优先', [], p, '广告投放助理', t)[0] == []
    assert screen_jd('负责门店入驻和团购上架，接受无商家拓展经验', [], p, '本地生活运营', t)[0] == []
    # 按单 / 按小时 / 按天计薪：不是月薪，直接不打分
    target = SimpleNamespace(min_pay=7)
    assert screen_pay('8-11元/单', target) == (['不是月薪（按单/按时/按天）'], 0)
    assert screen_pay('20-25元/时', target) == (['不是月薪（按单/按时/按天）'], 0)
    # 标题是设备调试、安装调试：偏硬件
    assert screen_jd('负责新设备安装调试，检验出货', [], p, '自动化设备调试工程师', t)[0] == ['偏硬件/现场']


def test_sales_wording_false_positives():
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 2.75}
    t = SimpleNamespace(max_years=3, min_pay=7, good_words=[])
    # 「接受无销售经验」「Amazon销售经验」「公司十余年生产销售经验」都不是销售岗
    assert screen_jd('接受无销售经验\n负责美团店铺数据分析', [], p, '美团店铺数据运营', t)[0] == []
    assert screen_jd('1年以上Amazon销售经验', [], p, '亚马逊运营助理', t)[0] != ['疑似销售岗']
    assert screen_jd('公司有十余年的生产销售经验', [], p, '跨境电商运营助理', t)[0] == []
    assert screen_jd('整理每日招募沟通、签约数据', [], p, '运营助理', t)[0] == []


def test_ai_bonus_one_year_ease_and_english_tag():
    p = {'edu': 3, 'full': 3, 'elite': False, 'years': 2.75}
    t = SimpleNamespace(max_years=3, min_pay=7, good_words=[])
    ai = '负责店铺日常维护，能利用AI工具提升日常产出效率'
    # 公司想用 AI 提效：+10；工资下限≥15K（高级岗）、会计这类职能不对口的标题不加
    normal = screen_jd(ai, [], p, '电商运营专员', t, '8-12K')[1]
    assert normal == screen_jd(ai, [], p, '电商运营专员', t, '20-30K')[1] - 10
    assert normal == screen_jd(ai, [], p, '电商会计', t, '8-12K')[1] - 10
    # 要 1 年没做过的领域经验：不扣分；高薪岗照旧扣
    assert screen_jd('1年以上亚马逊运营经验', [], p, '亚马逊运营助理', t, '8-12K')[1] <= 0
    assert screen_jd('1年以上亚马逊运营经验', [], p, '亚马逊运营助理', t, '20-30K')[1] > 0
    # 英语只挂在页面标签上：扣 10 分不压 50；正文写成要求：照旧压 50
    assert screen_jd('英语\n负责店铺日常维护', [], p, '亚马逊运营助理', t, '8-12K')[0] == ['页面标签带英语']
    assert screen_jd('1、英语四级及以上\n负责店铺日常维护', [], p, '亚马逊运营助理', t, '8-12K')[0] == ['要外语/粤语']
