from sqlalchemy.orm import Session
from types import SimpleNamespace
import re
from ..utils.pay import parse_pay_range
from ..utils.text import plain_text
# re【Python自带】，正则表达式工具，负责从文字中寻找数字。
from ..schemas import SkillMatchResult,KeywordMatchResult,ExpMatch,Dutyproof,RoleMatch,PrefMatch,JobRequirementResult,QuickJob,QuickScoreItem
from ..models import  Resume,ResumeAnalysis
from .semantic_service import embed_many,dot
SKIP_TAG=re.compile(r'年|大专|本科|硕士|博士|学历|经验不限|应届|不接受')
JOB_KEYWORDS = [
    'Python', 'FastAPI', 'MySQL', 'Redis', 'Docker',
    'RAG', 'Agent', 'Vue', 'JavaScript', 'CSS',
    'AI', '大模型', '产品设计'
]

# 经历匹配只使用已有技术词，宽泛词不能单独作为加分依据。
EXPERIENCE_KEYWORDS = [
    'Python', 'FastAPI', 'MySQL', 'Redis', 'Docker',
    'RAG', 'Agent', 'Vue', 'JavaScript', 'CSS',
    '大模型', '产品设计'
]
LEARNING_WORDS = (
    '正在学习',
    '正在自学',
    '计划学习',
    '目标是',
)
ROLE_KEYS=['Python','Vue','全栈','后端','前端','产品']
# 反向语义锚点：岗位标题跟这些方向更像时，直接判 0 分。
# 比关键词黑名单准——「AI短视频编剪师」标题里没有「剪辑」二字，
# 但它的语义跟「短视频剪辑师」的距离远近于跟「AI应用开发工程师」。
AVOID_ROLES = (
    '电话销售代表', '销售顾问', '客户经理', '课程顾问', '招商加盟',
    '内容运营', '直播运营', '新媒体运营', '市场推广专员',
    '短视频剪辑师', '视频制作师',
    '人力资源专员', '行政专员',
    '销售', '销售经理', '商务专员', '产品经理',
    # 技术岗不感兴趣：开发、测试、运维、实施、技术支持
    '软件开发工程师', '前端开发工程师', '程序员', '架构师', '测试工程师', '运维工程师', '实施工程师', '技术支持工程师',
    '硬件工程师', '硬件测试工程师', '电气工程师', '设备维修技术员', '机械工程师', '自动化设备操作员',
)

# 岗位性质不对，跟方向无关，语义抓不到，只能靠关键词
BLOCK_WORDS = (
    '实习', '见习', '兼职', '销售', '获客', '招商', '业务员', '合伙人',
    '硬件工程师', '硬件测试', '操作员', '装配', 'bd', '商务拓展',
    '剪辑', '主播',
    '高级', '资深', '专家', '总监', '负责人', '组长', 'leader', '架构师',
)
# 这两个词运营岗也常用：「独立站SEO运营+AI获客」「跨境电商AI操作员」，标题带运营类词就不拦
LOOSE_BLOCK = ('获客', '操作员')
# 管理岗：标题带主管 / 经理 / 店长，又不带专员、助理的，直接 0 分（「投放主管/专员」「经理助理」不拦）
MANAGER_TITLE = re.compile(r'主管|经理|店长')
JUNIOR_ROLE = re.compile(r'专员|助理|培训生|管培')
# 「电商总监助理」「总经理助理」是助理岗：判断排除词前先把「总监助理」当成「助理」
BOSS_ASSIST = re.compile(r'(?:总监|总经理|负责人|组长|老板|董事长)助理')
# 要百万、千万级的操盘成绩：「单店年销破千万的成功操盘案例」；「公司年营收过亿」这种介绍不算
BIG_CASE = re.compile(r'(百万|千万|亿).{0,12}案例|(操盘|打造).{0,10}(百万|千万|亿)')

# 只比「要避开的方向」像一点点不算数，
# 必须明显更像我要的岗位才给分。
AVOID_MARGIN = 0.08
# 标题里带这些词，说明是运营 / 投放岗，跳过反向锚点检查。
RESCUE_WORDS = ('运营', '投放', '优化师', '电商', '跨境', '亚马逊', '独立站')
# 方案里全是运营方向时，技术岗不要：标题带这些词、又不带「运营 / 投放 / 优化师」，直接 0 分
# 「AI应用工程师（跨境电商方向）」是开发岗；「跨境电商运营开发」带运营，照常打分
# 「产品开发助理（跨境电商）」是选品岗，不算写代码的开发
TECH_TITLE = re.compile(r'(?<!产品)(?<!商品)(?<!选品)开发|工程师|程序员|架构|算法|测试|运维|实施|技术|全栈|前端|后端')
OPS_ROLE = re.compile(r'运营|投放|优化师')
# 开发类标题：方案里有实施 / 技术支持方向也不算数，最像的方向得是开发或自动化方向
# 「软件工程师」最像「软件实施工程师」→ 不要；「Python自动化开发工程师」最像「Python自动化」→ 照常打分
DEV_TITLE = re.compile(r'(?<!产品)(?<!商品)(?<!选品)开发|研发|程序员|算法|架构|全栈|前端|后端|软件工程师')
DEV_DIR = re.compile(r'开发|自动化|python|rpa|程序', re.I)
# 开发岗标题至少要带当前方向的技术词；纯 Go/MES/数据开发不会因 JD 里堆了通用词而误过线。
TARGET_DEV = re.compile(r'(?<![a-z])ai(?![a-z])|agent|智能体|大模型|自动化|rpa|python', re.I)
# 这些是工业/产品外观设计，不属于当前AI实施、自动化、电商运营方向。
DESIGN_TITLE = re.compile(r'(?<![a-z])cmf(?![a-z])|工业设计|机械设计|结构设计|外观设计|产品设计师|平面设计|视觉设计|包装设计|ui设计|ux设计', re.I)
DESIGN_JD = re.compile(r'(?<![a-z])cmf(?![a-z])|autocad|keyshot|rhino|creo|工业设计|机械设计|结构设计|外观设计|色彩.{0,8}材质.{0,8}表面处理', re.I)
# 技术支持 / 实施类标题：JD 里硬件词明显比软件词多，就是硬件设备 / 网络设备支持，不是软件支持
SUPPORT_TITLE = re.compile(r'技术支持|支持工程师|应用工程师|fae|实施|售后|运维', re.I)
HW_TITLE = re.compile(r'设备调试|安装调试|调试工程师|电气调试|机械调试|现场调试')
HW_WORDS = re.compile(r'硬件|设备|仪器|仪表|传感器|电路|元器件|PLC|机器人|半导体|光学|激光|电气|电机|机械|示波器|万用表|驻厂|工厂|产线|芯片|模组|IVD|医疗器械|基因|测序|安装调试|上门|路由器|交换机|防火墙|组网|布线|弱电|数通', re.I)
SW_WORDS = re.compile(r'saas|软件|erp|crm|数据库|sql|api|接口|小程序|系统部署|云平台|云服务|rpa|影刀|低代码', re.I)
# 内容 / 新媒体 / 直播 / 策划类：JD 里没写 AI 工具或自动化工具，就压到 50
CONTENT_TITLE = re.compile(r'内容|新媒体|自媒体|直播|视频|剪辑|编导|主播|社媒|文案|创作|种草|策划|编辑')
# 学历等级：数字越大学历越高
EDU_RANK = {'高中': 1, '中专/中技': 1, '大专': 2, '本科': 3, '硕士': 4, '博士': 5}
# 简历里带这些字的行，才当作学历行
SCHOOL = re.compile(r'大学|学院|学校')
# 时间段，比如「2023.10-2026.07」或「2026.07-至今」
SPAN = re.compile(r'(\d{4})\.(\d{1,2})\s*[-—–~至]\s*(?:(\d{4})\.(\d{1,2})|至今)')
# 简历推荐的方向和某个反向锚点这么像，这个锚点就不再生效
OVERLAP = 0.70
# JD 句子里带这些词，说明是「优先 / 可选」，整句不算硬门槛
SOFT_WORDS = re.compile(r'优先|加分|或同等|亦可|均可|不限|之一|暂无|无需|不要求|无要求|没有要求|不作要求|放宽|可接受|接受.{0,6}经历|或具备|或者|或其他|是否')
# 简历学历行里带这些词，就不算全日制
NOT_FULLTIME = re.compile(r'成人|自考|函授|网络教育|远程|业余|夜大|开放大学')
ELITE = re.compile(r'985|211|双一流|QS\s*Top|C9')
# 要求的年限：「3-5年」「三年以上」「5年+」都取下限
YEARS_NEED = re.compile(r'(?<![第\d.])([1-9]\d?|[一两二三四五六七八九十])\s*(?:[-~～—–至到]\s*\d{1,2}\s*)?(?:年以上|年及以上|\+\s*年|年\s*\+|年左右|年\S{0,16}经验)')
# 「3年以下」是上限，不是至少要3年；「工作经验至少3年」则是最低要求。
YEARS_UPPER = re.compile(r'(?:不超过|少于|低于|不满|未满|至多)\s*[一两二三四五六七八九十\d]+\s*年|[一两二三四五六七八九十\d]+\s*年(?:以下|以内)')
YEARS_AFTER = re.compile(r'(?:工作经验|相关经验|工作年限).{0,8}?(?:不少于|至少|最低|要求)?\s*([1-9]\d?|[一两二三四五六七八九十])\s*年')
CN_NUM = {'一': 1, '两': 2, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
# 句首序号「2.」「（3）」「-」，不去掉会把「2.3 年以上」读漏
LIST_NO = re.compile(r'^\s*(?:[（(]\s*\d{1,2}\s*[)）]|\d{1,2}\s*[.、．)）]|[-•·●])\s*')
# 我简历里做过的领域（抖音本地生活运营）：年限要求写的是这些，才按经验上限比
# 「商家 / 商户」不算：阿里国际站、亚马逊的岗位也叫商家运营
# 单写「抖音」也不算：我做的是抖音本地生活，抖音电商 / 抖店 / 直播按没做过的领域算；只写「抖音运营」没点名领域，照常
MY_FIELD = re.compile(r'本地生活|团购|到店|抖音来客|美团|点评|门店')
# 我没做过的领域：年限要求点名这些（「2年以上亚马逊广告投放经验」），我一年都没有，直接不符合
OTHER_FIELD = re.compile(
    r'电商|亚马逊|amazon|跨境|tiktok|shopee|temu|lazada|独立站|速卖通|阿里巴巴国际站|国际站|阿里巴巴|(?<!\d)1688(?!\d)|b2b|'
    r'外贸|海外|淘宝|天猫|京东|拼多多|抖店|小店|带货|快手|小红书|视频号|'
    r'直播|社媒|新媒体|内容|广告|投放|信息流|千川|seo|sem|软件|实施|开发|测试|运维|技术|工程师|售前|产品|设计|销售|客服|'
    r'财务|人事|行政|金融|教育|医疗|法律|游戏|硬件|嵌入式|算法|项目管理|erp|saas|crm|rpa|python|java|'
    r'(?<![a-z])ai(?![a-z])|人工智能|大模型|智能体|agent',
    re.I,
)
# 外语 / 方言要求：我不会
LANG = re.compile(r'英语|英文|cet-?[46]|四级|六级|雅思|托福|粤语|广东话|日语|韩语|葡语|西班牙语|德语|法语|俄语', re.I)
LANG_REQUIRED = re.compile(r'(?:英语|英文).{0,12}(?:要过|必须|要求|工作语言|四级|六级|4/6级)|(?:必须|要求).{0,12}(?:英语|英文)', re.I)
# 应届生岗位：写了届别（「2026届」「26届」「25/26届」「26年毕业」「27届本科」）、校招、「学历…应届毕业生」→ 只招应届，压到 50
# 届别后面写了「亦可 / 优先 / 接受」、或者「应届毕业生优先」→ 扣 10 分；只写「接受 / 欢迎应届生」、没写届别的不扣（也收有经验的人）
# 「暂无2026届招聘需求」「2026届请勿投递」「第26届广交会」不算
GRAD_YEAR = re.compile(r'(?<![第\d.])(?<!连续)(?:20)?2[3-9]\s*(?:[/、\-~～至]\s*(?:20)?2[3-9]\s*)?(?:届|级|年毕业|年应届|应届)(?!.{0,6}(?:广交会|展会|大会|博览|峰会))|校招(?:储备)?岗|校园招聘|校招计划')
GRAD_PREFER = re.compile(r'应届(?:毕业)?生?[^，,。；;\n]{0,4}优先')
GRAD_BARE = re.compile(r'应届(?:毕业)?生')
GRAD_OPTIONAL = re.compile(r'亦可|也可|均可|即可|可投|接受|欢迎|可考虑|可放宽|优先|加分|或|可以|皆可')
NOT_GRAD = re.compile(r'请勿|勿投|不招|暂无|不用投|不考虑|谢绝')
GRAD_SOFT = '面向应届生'
GRAD_CUT = 10
# 硬门槛：命中就把分数压到 50，不再推荐（另外「要N年…经验」也算；「HR超过3天未活跃」「薪资上限不超过…」直接 0 分）
HARD_FLAGS = (
    '要985/211', '要全日制本科', '要硕士', '疑似销售岗', '偏硬件/现场',
    '要证书', '要打电话', '内容岗没要求AI工具', '偏算法/模型训练',
    '需独立负责大型项目', '偏高级基础设施', '偏工业/产品设计', '只招应届', '要外语/粤语', '要百万级操盘案例',
    '偏客服/中控', '不收新手', '要独立运营经验', '超出年龄要求', '偏剪辑/设计',
    '要带团队', '要主导架构设计', '开发语言不是Python/JS',
)
# 开发岗 JD 写的语言：用 Java / Go / C++ / PHP / 安卓 / iOS / 嵌入式…，标题和 JD 又都没提 Python / JS / 前端框架
OTHER_LANG = re.compile(r'java(?!\s*script)|golang|go\s*语言|(?:使用|熟悉|精通|掌握|熟练)\s*go(?![a-z])|c\+\+|c#|\.net|php|kotlin|swift|objective-c|android|ios开发|嵌入式|单片机|verilog|fpga', re.I)
MY_LANG = re.compile(r'python|javascript|typescript|(?<![a-z])js(?![a-z])|vue|react|node', re.I)
DEV_LANG_FLAG = '开发语言不是Python/JS'
# 标题直接写明的语言：「C++ 客户端开发工程师」「Java开发」「Android研发」
TITLE_LANG = re.compile(r'java(?!\s*script)|golang|(?<![a-z])go(?![a-z])|c\+\+|c#|\.net|php|kotlin|swift|android|安卓|(?<![a-z])ios(?![a-z])|嵌入式|单片机|(?<![a-z])qt(?![a-z])', re.I)
# JD 里「加分项」小标题：后面几行是加分，不是硬要求
BONUS_HEAD = re.compile(r'^(?:加分项?|加分条件|优先条件|优先考虑|以下优先|有以下.{0,10}优先)\s*[:：]?$')
SECTION_HEAD = re.compile(r'^(?:岗位职责|工作职责|职位描述|任职要求|岗位要求|任职资格)')
HARD_CAP = 50
# 工资下限在期望下方 1K 以内（6-10K）：轻扣 5 分
PAY_SOFT_CUT = 5
# 没读过 JD 的岗位最高 54 分：只看了标题不算数，排在「可投可不投」的 55 分以下
NO_JD_CAP = 54
# 备选方向（比如 ERP / SaaS 实施）：只对上备选方向的岗位扣 5 分，排在主投方向后面
BACKUP_CUT = 5
# 进公司有人带教的岗位（有人带、导师一对一、带薪培训、重点培养、接受小白…）：
# 没踩硬门槛、没要求 1 年没做过的经验、不是面向应届生、标题分不低于 30，至少 60 分
MENTOR = re.compile(
    r'有人带|专人带|主管带|老员工带|前辈带|师傅带|老带新|师带徒|传帮带|手把手|一对一带|1对1带|一带一|带教|导师|包教包会|从零教|从0教|'
    r'可培养|重点培养|从零培养|长期培养|公司培养|储备培养|培养计划|培养体系|'
    r'入职培训|岗前培训|上岗培训|新人培训|系统培训|系统化培训|带薪培训|免费培训|专业培训|提供培训|培训体系|完善的培训|定期培训|'
    r'接受小白|小白可|新手可|接受新人|接受转行|零基础|0基础|无经验可|可无经验|接受无经验|无经验亦可|无经验也可'
)
# 是你去带别人、去培训客户，不算：「负责新人带教」「担任导师」「讲师」「客户培训」
MENTOR_NOT = re.compile(r'负责[^，,。；;]{0,8}(?:带教|培训|导师|培养)|带教新人|培训新人|担任导师|新人导师|讲师|培训师|客户培训|用户培训|培训客户|培训用户')
MENTOR_FLOOR = 60
# 标题分太低（完全不像你的方向，比如 PMC 计划员）的，写了带教也不保底
MENTOR_TITLE_MIN = 30
MENTOR_HIT = '有人带/可培养'
# 公司想用 AI 提效 / 接入 AI：JD 写了「用 AI 工具提升效率」「接入大模型」「搭建 Coze/Dify 工作流」这类，+10 分
AI_TERM = r'(?<![a-z])ai(?![a-z])|人工智能|大模型|aigc|智能体|agent|llm'
AI_WANT = re.compile(
    r'(?:' + AI_TERM + r')[^，,。；;\n]{0,12}(?:提效|提升效率|效率|赋能|落地|应用|工具|工作流|自动化|转型|接入|集成|辅助|优化)|'
    r'(?:提效|降本增效|提升效率|提高效率|数字化转型|智能化转型|智能化升级)[^，,。；;\n]{0,12}(?:' + AI_TERM + r')|'
    r'(?:接入|引入|搭建|使用|运用|熟练使用|会用|善用|借助|利用)[^，,。；;\n]{0,8}(?:' + AI_TERM + r'|coze|扣子|dify|n8n|chatgpt|deepseek|豆包|kimi|通义|文心|gpt|即梦|可灵)|'
    r'coze|扣子|dify|n8n|智能体搭建|工作流搭建|提示词',
    re.I,
)
AI_BONUS = 10
AI_HIT = '用AI提效'
# 工资下限≥15K：标签写「1-3年」也多半是高级岗，不享受「1年经验不扣分」和 AI 加分
SENIOR_PAY = 15
# 职能不对口的标题（会计、采购、设计、老师、算法、Golang/Java/Android…）：同样不享受
NON_FIT = re.compile(r'会计|财务|出纳|采购|跟单|设计|cmf|结构|美工|maya|blender|unity|老师|讲师|教师|硬件|嵌入式|算法|量化|android|ios|golang|java|c\+\+|c#', re.I)
# 英语只挂在页面标签上（单独一行「英语」）、正文没写成要求：不压到 50，扣 10 分
LANG_TAG_FLAG = '页面标签带英语'
LANG_TAG_CUT = 10
# 招聘者活跃度：JD 里单独一行的活跃标签
ACTIVE_LINE = re.compile(r'(在线|刚刚活跃|今日活跃|\d+日内活跃|本周活跃|\d+周内活跃|本月活跃|\d+个?月内活跃|近半年活跃|半年前活跃)')
# 在线、刚刚、今天活跃不扣分；1～3日内活跃（包括 3 日）扣 5 分；比 3 天更久没活跃直接不打分。
ACTIVE_OK = ('在线', '刚刚活跃', '今日活跃')
HR_RECENT_CUT = 5
# 没做过的领域要 1 年或半年经验：扣 10 分，不拦（要 2 年及以上的直接压到 50）
NEW_FIELD_CUT = 10
# 没做过的领域要 1 年：方向很对口（标题对上求职方向）时只扣 5，其余扣 10
# JD 技术词多不再算放宽条件——关键词不能顶替「没做过这行」
NEW_FIELD_EASE = 5
# 年限句里的「可选」词。「X、Y 其中之一运营经验」不算可选，所以这里没有「之一」
# 「跨境平台不限」「类目不限」只是平台随意，不代表经验可选
YEARS_SOFT = re.compile(r'优先|加分|或同等|亦可|均可|(?<!平台)(?<!类目)(?<!行业)(?<!专业)(?<!品类)(?<!站点)(?<!学历)不限|暂无|无需|不要求|放宽|可接受|或者|是否')
HALF_YEAR = re.compile(r'(?:半年|[1-9]\s*个月|三个月|六个月)(?:以上|及以上)?[^，,。；;]{0,16}经验')
# 写了接受新人：标签「1-3年」不扣分；和年限要求写在同一行，那条年限也不扣
ACCEPT_NEW = re.compile(
    r'接受.{0,4}(?:小白|新人|新手|应届|零基础|0基础|转行)|接受无.{0,8}经验|无.{0,6}经验(?:也可|亦可|可)|'
    r'0基础|零基础|小白.{0,4}(?:可|也可|亦可)|可培养|有人带|带教|经验不限|不限经验|无需经验|'
    r'应届生?.{0,10}(?:也可|亦可|可考虑|可投|均可)'
)
STALE_HR = 'HR超过3天未活跃'
# 工资最高也不超过期望（4-7K、5-6K）：直接 0 分，不读 JD；跨过期望（6-8K）只扣 5 分
LOW_PAY = '薪资上限不超过'
# 下限比期望低 1K 以上（期望 7K 时下限不到 6K）：直接排除；下限在 6～7K 之间只扣 5 分
LOW_FLOOR = '薪资下限不到'
PAY_FLOOR_GAP = 1
# 按单 / 按小时 / 按天计薪（外卖骑手、兼职、日结）：不是月薪，直接不打分
PIECE_PAY = '不是月薪（按单/按时/按天）'
PIECE_UNIT = re.compile(r'元\s*/\s*(?:单|件|次|时|小时|天|日|周)')
# 本地生活（美团 / 团购 / 到店 / 外卖）是我做过的：这类岗位写「不接受小白」「要独立运营」我也符合
LOCAL_LIFE = re.compile(r'本地生活|团购|到店|美团|点评|外卖|抖音来客|即时零售|闪购|饿了么')
# 客服 / 直播中控岗：标题写明（AI 客服系统类不算），或者 JD 要客服 / 中控经验、主要做客服、要求打字速度
SERVICE_TITLE = re.compile(r'客服|中控|场控')
AI_SERVICE = re.compile(r'(?<![a-z])ai(?![a-z])|智能|机器人|大模型|系统', re.I)
SERVICE_JD = re.compile(
    r'(?:有|具备|熟悉|做过|需要?)[^，,。；;]{0,8}(?:中控|客服)(?:相关)?(?:工作)?(?:经验|经历|系统)|'
    r'(?:负责|统筹|处理|承担)[^，,。；;]{0,10}客服(?:工作|接待)|中控操作|打字速度'
)
# 明确不收新人：「拒绝新手小白」「不招没经验的」「无经验勿扰」「不接受无经验牛人」
REJECT_NEW = re.compile(
    r'拒绝(?:新手|小白|无经验)|不(?:接受|要|招|考虑|支持)(?:新手|小白|无经验|没经验|零基础)|暂不考虑小白|'
    r'(?:小白|新手|无经验|没经验)[^，,。；;]{0,4}(?:勿扰|勿投|慎投|免谈|绕道)'
)
# 要能独立运营店铺 / 账号：「1-3年独立运营」「有独立运营经验」「独立负责淘宝店铺的全盘运营」
SOLO_RUN = re.compile(
    r'\d\s*(?:[-~～—–至到]\s*\d+\s*)?年\S{0,4}独立(?:运营|操盘)|'
    r'独立(?:运营|操盘|负责)[^，,。；;]{0,6}(?:店铺|账号|整店|全盘|平台)|独立(?:运营|操盘)(?:经验|能力)|'
    r'独立(?:店铺|账号)操盘|独立完成[^，,。；;]{0,4}(?:店铺|账号)[^，,。；;]{0,4}运营|'
    # 「能够独立操作店铺」算；「能独立操作店铺后台」只是会用后台，不算
    r'独立操作[^，,。；;]{0,6}(?:店铺|整店)(?!后台)'
)
# 以后才独立运营的不算：「学习后可以独立运营店铺」「优秀者可独立负责」「独立操盘IP账号，成长空间大」
SOLO_LATER = re.compile(r'(?:学习|上手|熟悉|转正|入职|培训|考核|运营)后|逐步|培养|晋升|优秀者|成长|未来|将来|机会')
# 年限写「相关经验」、没点名领域：领域看标题（「亚马逊运营专员」要「1年以上相关经验」= 要 1 年亚马逊经验）
RELATED = re.compile(r'相关|同类|同岗|类似|本岗')
# 要带团队：「带领3-5人小团队」「团队管理能力」「有带团队的经验」（「管理1人」「搭建团队知识库」不算）
TEAM_LEAD = re.compile(
    r'(?:带领|带|管理|领导)\s*\d+\s*(?:[-~～—–至到]\s*\d+\s*)?(?:人|名)(?:以上|左右)?[^，,。；;]{0,4}(?:团队|小组)|'
    r'(?:团队管理|管理团队|带团队|人员管理)(?:的)?(?:能力|经验)|带过团队'
)
# 要主导架构设计：「主导AI技术架构设计」「负责产品的架构设计」「架构设计经验」
ARCH_LEAD = re.compile(r'主导[^，,。；;]{0,8}架构|负责[^，,。；;]{0,10}架构设计|架构设计(?:经验|能力)|系统架构师')
# 以后才带团队、欢迎但不强求的不算：「表现优秀者可定位为主管」「欢迎带过团队的候选人」
LEAD_LATER = re.compile(r'优秀者|表现优秀|晋升|发展为|往管理|意愿|未来|将来|可定位|欢迎|成熟后|直接面试')
# JD 的年龄要求：「18-25岁」「年满21-27周岁」「32 周岁及以下」「30岁以内」
AGE_RANGE = re.compile(r'(?<!\d)(1[6-9]|[2-5]\d)\s*[-~～—–至到]\s*([2-5]\d)\s*周?岁')
AGE_UPPER = re.compile(r'(?<!\d)([2-5]\d)\s*周?岁\s*(?:及以下|以下|以内|之内)')
# 简历里的年龄：「26岁」或者出生年份
RESUME_AGE = re.compile(r'(?<![\d\-~～至到])([1-6]\d)\s*岁(?!以)')
RESUME_BIRTH = re.compile(r'(?:出生|生日)\D{0,6}((?:19|20)\d{2})')
# 不算销售的写法：「降低获客成本」「团购引流获客」「抖音本地推」「接受无商家拓展经验」
# 「接受无销售经验」「接受无海外销售经验」说的是不要销售经验，也先删掉
NOT_SALES = re.compile(r'获客成本|引流获客|本地推|无商[家户]拓展经验|无[^，,。；;]{0,8}销售经验')
# 一看就是销售 / BD 的说法：单独出现就算（整行写了优先、「无需」的不算）
STRONG_SALES = re.compile(
    # 只认带限定词的销售经验：「Amazon销售经验」是电商运营经验，「十余年生产销售经验」是公司介绍，都不算
    r'(?:广告|渠道|大客户|电话|商务|to\s*b|对机构|对企业|软件|信息化服务)[^，,。；;]{0,8}销售(?:工作)?经验|'
    r'商[家户]的?开拓|开拓[^，,。；;]{0,4}商[家户]|客户拓展|洽谈[^，,。；;]{0,6}签约|促进[^，,。；;]{0,6}签约|签约数(?!据)',
    re.I,
)
# 主要做剪辑 / 作图的岗位：要求熟练剪映、PS，或者独立完成图片设计、海报排版、视频剪辑
# 「会基础PS」「有PS功底」「配合美工完成主图」不算，普通运营助理也常这么写
DESIGN_WORK = re.compile(
    r'独立完成[^，,。；;]{0,12}(?:(?:图片|视觉|平面|海报|详情页?|主图|基础|美工|图文)设计|剪辑|排版|海报|修图|作图|拍照|拍摄|图文|素材制作)|'
    r'(?:熟练|精通)[^，,。；;]{0,10}(?:剪辑|剪映|作图|修图|美图秀秀|醒图|photoshop|premiere|(?<![a-z])(?:ps|pr|ae)(?![a-z]))|剪辑熟练',
    re.I,
)
# JD 里「在做销售」的词和「销售式薪资」的词，两类同时出现才算销售岗
SALES_DO = ('拓客', '获客', '陌拜', '地推', '电销', '签单', '开单', '开发客户', '拓展客户', '客户开发', '销售线索', '招商', '邀约客户',
            '商户拓展', '商户的拓展', '拓展商户', '商家拓展', '拓展商家', '从事销售')
SALES_PAY = ('底薪', '提成', '业绩', '成交', '客户资源')
# JD 里出现这些，说明主要做设备维修、工厂倒班、现场调试，不是运营岗
FIELD_WORDS = ('维修', '倒班', '夜班', '现场调试', '示波器', '万用表', '装机', '电工', '焊接')
# 必须持证、主要靠打电话：写成硬要求就压到 50（「要求精通」可以及格，不拦）
CERT = re.compile(r'(须|需|必须|要求|持有|具备|取得|拥有).{0,12}(证书|资格证|执业证|上岗证)|持证上岗')
# SSL / 数字证书这类是技术活，不是职业资格证
CERT_TECH = re.compile(r'ssl|https|数字证书|ca证书|证书配置|证书部署|证书管理|证书申请|加密|签名', re.I)
PHONE = re.compile(r'电话.{0,12}(沟通|联系|回访|邀约|营销|销售)|(沟通|回访|邀约).{0,6}电话|电销|外呼|打电话|话务|电话客服')
# 上面两条只认这几个「可选」词——「或者」照样是硬要求
PREFER = re.compile(r'优先|加分|更佳|更好|最好|最佳')
# 「只投初级」的方向：岗位标题要带这些词才给分
JUNIOR = re.compile(r'初级|助理|应届|培训生|管培|储备|学徒|入门|小白')
# 加分词的同义说法：JD 很少原样写「提供培训」，常写「系统培训」「带教」
GOOD_ALIAS = {
    '经验不限': r'经验不限|不限经验|无需经验|无经验要求|零经验|可无经验|接受无经验|无经验可|无经验也可|无经验亦可|0基础|不要求经验',
    '接受转行': r'转行|零基础|小白',
    '初级': r'初级|入门|应届',
    '助理': r'助理',
    # 「负责客户培训」是你去培训客户，不算公司培养你
    '提供培训': r'(?<!客户)(?<!用户)(?<!商家)(?<!学员)(?<!产品)(?<!技术)培训(?!客户|用户|商家|学员)|带教|有人带|老带新|师傅带',
}
# 加分词每个 5 分，标题 + 标签 + JD 合起来最多 10 分
GOOD_EACH, GOOD_MAX = 5, 10
# 否定说法：「无需电话销售」「不做电销」不算
NOT_DO = re.compile(r'不[是做需用打]|非电|无需|无电|拒绝|没有')
# 加分：写了 AI 工具 +10，写了自动化工具 +5
# 不用 \b：中文紧挨英文时（「使用GPT」）两边都算单词字符，\b 会失效
AI_TOOL = re.compile(r'gpt|codex|claude|cursor|copilot|trae|deepseek|豆包|kimi|通义|文心|智谱|coze|扣子|dify|n8n|aigc|ai\s*工具|大模型|智能体|agent', re.I)
# 内容 / 直播岗常写「短视频脚本」，那是视频脚本；只有 Python / 自动化脚本才算
AUTO_TOOL = re.compile(r'python|rpa|影刀|自动化|(?:python|自动化|js|rpa)\s*脚本|多维表|低代码|sql|(?<![a-z])api(?![a-z])|接口|爬虫|工作流', re.I)
# 跟简历经历相关的 7 类：命中 2 类加 5 分，4 类加 10 分
RESUME_CONTENT = (
    r'抖音|巨量|千川', r'本地生活|到店|团购|美团|点评', r'门店|商家|商户', r'达人|kol|网红',
    r'付费推广|投放|广告|roi', r'数据分析|复盘|报表', r'舆情|评价|口碑',
)

# 免费粗筛使用的企业业务词；只做本地字符串匹配，不调用大模型。
BUSINESS_WORDS = (
    'ERP', 'CRM', 'Excel', '数据分析', 'API', '自动化', '商品上架',
    '订单', '库存', '广告投放', 'ROI', '报表', 'SaaS', '系统对接',
)
BUSINESS_EACH, BUSINESS_MAX = 4, 24

# JD 粗筛能力项：同一项里的同义词只计一次，不因关键词重复堆分。
# 分值来自用户的求职能力清单；粗筛完全在本地运行，不调用大模型。
JD_REQUIREMENTS = (
    ('Python', 2, r'python'),
    ('Web框架', 2, r'fastapi|flask|django'),
    ('SQL/数据库', 2, r'(?<![a-z])sql(?![a-z])|mysql|sqlite|sqlalchemy|(?<![a-z])orm(?![a-z])|数据库'),
    ('API/接口', 2, r'(?<![a-z])api(?![a-z])|restful?|http|json|接口(?:开发|调用|对接|集成)?|第三方接口'),
    ('RAG/知识库', 2, r'(?<![a-z])rag(?![a-z])|知识库|embedding|向量(?:检索|数据库|搜索)|milvus|faiss|chroma'),
    ('Agent/工具调用', 2, r'智能体|(?<![a-z])agent(?![a-z])|tool\s*calling|function\s*calling|工具调用|工作流编排'),
    ('大模型API/Prompt', 2, r'大模型|llm|prompt|提示词|openai|chatgpt|deepseek|claude|通义|模型接口'),
    ('Vue/前端', 1, r'(?<![a-z])vue(?:\.js|\s*3)?(?![a-z])|javascript|html|css|axios|前端(?:开发|技术|框架|页面|工程)'),
    ('Git', 1, r'(?<![a-z])git(?:hub)?(?![a-z])'),
    ('Redis', 1, r'(?<![a-z])redis(?![a-z])'),
    # 「项目上线」不是部署运维，不算
    ('Docker/Linux部署', 1, r'docker(?:\s*compose)?|linux|nginx|部署'),
    ('Excel/Pandas', 1, r'excel|pandas|数据透视表'),
    ('数据分析/报表', 2, r'数据分析|数据清洗|数据处理|数据统计|经营分析|效果分析|报表|复盘'),
    ('需求分析/方案', 1, r'需求(?:调研|分析|梳理|拆解|沟通)|业务流程|流程优化|技术方案|解决方案|方案设计|跨部门'),
    ('AI实施/交付', 2, r'(?:ai|人工智能|大模型|智能体).{0,8}(?:实施|交付|落地|集成|配置)|客户需求|客户沟通|客户培训|用户培训|效果测试|问题排查|故障排查|数据导入'),
    ('RPA/业务自动化', 2, r'(?<![a-z])rpa(?![a-z])|影刀|uibot|uipath|power\s*automate|selenium|playwright|浏览器自动化|流程自动化|业务自动化|自动化脚本|(?<!及其)自动化'),
    ('AI工具/低代码', 1, r'dify|coze|扣子|n8n|langchain|llamaindex|低代码|ai\s*工具'),
    ('SaaS/ERP实施', 2, r'(?<![a-z])saas(?![a-z])|(?<![a-z])erp(?![a-z])|(?<![a-z])crm(?![a-z])|(?<![a-z])wms(?![a-z])|(?<![a-z])mes(?![a-z])|金蝶|用友|系统实施|软件实施|系统配置|权限配置'),
    ('跨境电商经验', 0, r'跨境电商|amazon|亚马逊|tiktok\s*shop|temu|shopee|lazada|ebay|独立站'),
    ('电商平台/运营', 2, r'跨境电商|电商运营|店铺运营|amazon|亚马逊|tiktok|抖音|temu|shopee|独立站|平台规则'),
    ('库存/仓储经验', 0, r'库存|仓储|仓库|(?<![a-z])wms(?![a-z])'),
    ('商品/订单/库存', 1, r'商品上架|listing|订单|库存|仓储|物流|sku'),
    # 短英文词要单独成词：「Electron」里的 ctr、「Android」里的 roi 不算
    ('广告投放/数据指标', 2, r'广告投放|信息流|(?<![a-z])(?:sem|roi|roas|cpa|cpc|ctr|cvr)(?![a-z])|百度推广|巨量|千川|google\s*ads|meta\s*ads|tiktok\s*ads|转化率|投放报表'),
    ('个人项目/作品', 3, r'个人项目|github|作品集|作品展示|(?:demo|poc)(?:经验|项目|案例|展示)?'),
    ('接受0-1年/经验不限', 3, r'经验不限|不限经验|无需经验|无经验要求|零经验|0\s*[-~～—至到]\s*1\s*年|1\s*年以内|应届生'),
    ('接受项目经验', 3, r'项目经验(?:即可|亦可|优先|可替代)|有项目经验者|接受.{0,6}项目经验|项目经历(?:即可|亦可|优先)'),
)

CORE_MODEL_RISK = re.compile(
    r'(?:大模型|模型|算法).{0,10}(?:预训练|训练研发|核心训练|算法研发|研究)|'
    r'(?:预训练|分布式训练|cuda|高性能推理|顶会论文|论文发表)', re.I
)
LARGE_PROJECT_RISK = re.compile(r'独立(?:负责|承担|主导).{0,20}(?:大型|核心|千万级|百万级)项目|千万级项目', re.I)
ADVANCED_INFRA_RISK = re.compile(r'百万\s*qps|超高并发|kubernetes.{0,8}(?:集群|运维|底层)|k8s.{0,8}(?:集群|运维|底层)', re.I)

AI_TERMS=('ai','人工智能','大模型','智能体','agent')
# 电商运营方向认的平台词：「京东运营」「天猫运营」「抖店运营」标题里没写「电商」也算
ECOM_TERMS=('电商','淘宝','天猫','京东','拼多多','抖店')
JUNIOR_TERMS=('助理','初级','专员','顾问','工程师','实施','交付')
TITLE_RULES={
    'AI实施助理':(AI_TERMS,('实施','交付')),
    'AI应用助理':(AI_TERMS,('应用','项目','流程'),JUNIOR_TERMS),
    'RPA助理':(('rpa',),('助理','实施','开发','工程师','专员')),
    'Python自动化':(('python',),('自动化',)),
    '业务自动化':(('自动化',),('业务','流程','办公','电商','跨境','rpa','python')),
    'SaaS实施助理':(('saas',),('实施','交付','顾问','助理')),
    'ERP实施助理':(('erp','金蝶','用友'),('实施','顾问','交付','助理')),
    '跨境电商运营助理':(('跨境','跨境电商'),('运营',)),
    'Amazon运营助理':(('amazon','亚马逊'),('运营',)),
    '亚马逊运营助理':(('amazon','亚马逊'),('运营',)),
    'TikTok运营助理':(('tiktok',),('运营',)),
    'Temu运营助理':(('temu',),('运营',)),
    # 标题没写「助理 / 初级」也算（用户 2026-09-17 放宽）：「国内电商运营」「抖音电商运营」；主管 / 经理 / 高级 / 负责人另有规则拦
    '电商运营助理':(ECOM_TERMS,('运营',)),
    # 方向名不带「助理」：「国内电商运营」「facebook广告投放」跟「…助理」的名字不够像，标题分偏低
    '电商运营':(ECOM_TERMS,('运营',)),
    '商家运营':(('商家','商户'),('运营',)),
    '本地生活运营':(('本地生活','美团','外卖','团购','点评','到店','闪购','饿了么','即时零售'),('运营',)),
    '电商数据运营':(('电商',),('数据',),('运营',)),
    # 「投放助理」「短剧投放助理」没写「广告」也算；「facebook广告投放」没写助理 / 专员也算（用户 2026-09-17 放宽）
    '广告投放助理':(('投放','信息流','千川','广告优化'),),
    '广告投放':(('投放','信息流','千川','广告优化'),),
    # AI 运营 / Agent 开发 / AI 开发助理 / AI 技术支持：泛泛的「AI工程师」「机器人AI工程师」不算
    'AI运营助理':(AI_TERMS+('aigc',),('运营',)),
    'Agent应用开发':(('agent','智能体','大模型','llm','aigc'),('开发','工程师','研发')),
    'AI开发助理':(AI_TERMS,('开发','研发'),('助理','初级','应届','培养','无经验','小白')),
    'AI技术支持':(('技术支持','客户成功','售前支持'),('ai','人工智能','智能体','agent','saas','软件','rpa','系统')),
    '数字化实施':(('数字化','信息化','oa实施','crm','wms','mes实施'),('实施','顾问','助理','专员','工程师')),
    # 电商里的自动化 / 数据岗；「自动化控制工程师」这种工业自动化不算
    '电商自动化':(('自动化',),('亚马逊','amazon','tiktok','电商','跨境','数据','报表','excel','运营')),
    '电商数据专员':(('电商','跨境'),('数据',),('专员','分析','助理')),
    # 写代码的开发岗（用户 2026-09-17 加的主投方向）；算法、架构师不算，「高级 / 资深 / 专家」照样被排除词拦
    '软件开发':(('开发','研发','程序员','全栈','前端','后端','软件工程师'),),
}
# 「产品开发」「市场开发」「客户开发」不是写代码：标题按方向匹配前先去掉
NOT_DEV_WORDS = re.compile(r'产品开发|商品开发|选品开发|市场开发|客户开发|业务开发|渠道开发')


# 要求写得很深（精通 / 独立负责 / 3年以上）的能力项不算加分：要求越高的岗位不该越容易被推荐
DEEP_REQ = re.compile(r'精通|深入理解|深入掌握|独立负责|独立设计|独立开发|独立完成|资深|专家|[3-9]\s*年', re.I)


def business_hits(text:str)->list[str]:
    low=(text or '').lower()
    return [word for word in BUSINESS_WORDS if word.lower() in low]


def requirement_hits(text:str)->tuple[list[str],int]:
    """返回 JD 命中的不同能力项和总分；同一项无论出现多少次都只计一次。"""
    hits=[]
    points=0
    sentences=[s for s in re.split(r'[。；;\n！!]',text or '') if s.strip()]
    for name,weight,pattern in JD_REQUIREMENTS:
        matched=[s for s in sentences if re.search(pattern,s,re.I)]
        # 这一项全都写在「精通 / 独立负责 / 3年以上」的句子里，就不算加分
        if not matched or all(DEEP_REQ.search(s) for s in matched):
            continue
        hits.append(name)
        points+=weight
    return hits,points


def title_rule_match(title:str,positions:list[str])->bool|None:
    rules=[TITLE_RULES[p] for p in positions if p in TITLE_RULES]
    # 自定义方案只要含有未知方向，就保留原来的语义匹配；整套都是标准方向时才启用严格门禁。
    if not rules or len(rules)!=len(positions):
        return None
    low=NOT_DEV_WORDS.sub('',re.sub(r'\s+','',title.lower()))
    return any(all(any(word.lower() in low for word in group) for group in rule) for rule in rules)

def is_learning_text(text: str) -> bool:
    return any(
        word in text
        for word in LEARNING_WORDS
    )

def find_resume_evidence(
        responsibility:str,work_experience:list[str]
)->str | None:
    responsibility_lower = responsibility.lower()
    for evidence in work_experience:
        if is_learning_text(evidence):
            continue

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
    all_skills=[job_skills,*ai_required_skills]
    return sorted(skill_names(all_skills))

def calculate_skill_score(
        resume_skill:list[str],
        job_skills:list[str]
)->SkillMatchResult:
    resume_set = skill_names(resume_skill)
    job_set = skill_names(job_skills)
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
def skill_names(items: list[str]) -> set[str]:
    return {
        skill_name(part)
        for text in items
        for part in re.split(r'[/,，、]+', text)
        if part.strip()
    }

def build_job_requirements(
        job_skills: str,
        description: str
) -> JobRequirementResult:
    duties = [
        text.strip()
        for text in re.split(r'[；;。\n]+', description)
        if text.strip()
    ]
    return JobRequirementResult(
        responsibilities=duties,
        required_skills=sorted(skill_names([job_skills])),
        experience=[],
        education=[],
        bonus_points=[]
    )



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
    resume_keywords = skill_names(resume_skills)
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
    resume_set = skill_names(resume_skills)
    required_set=skill_names(required_skills)
    matched_skills = resume_set & required_set
    # &：【语言固定】，计算两个集合的交集。
    if not required_set:
        return SkillMatchResult(score=0,matched_skills=[],missing_skills=[])
    return SkillMatchResult(score=round(len(matched_skills)/len(required_set)*15),
        matched_skills=sorted(matched_skills),
        missing_skills=sorted(required_set-resume_set)
        )

def read_edu(lines):
    return max(
        (rank for line in lines if SCHOOL.search(line)
         for name, rank in EDU_RANK.items() if name in line),
        default=0
    )


def read_years(lines, today):
    months = 0
    for line in lines:
        if '公司' not in line:
            continue
        for m in SPAN.finditer(line):
            y1, m1 = int(m.group(1)), int(m.group(2))
            if m.group(3):
                y2, m2 = int(m.group(3)), int(m.group(4))
            else:
                y2, m2 = today.year, today.month
            months += max((y2 - y1) * 12 + (m2 - m1), 0)
    return months / 12 if months else None

def read_fulltime_edu(lines):
    return max(
        (rank for line in lines if SCHOOL.search(line) and not NOT_FULLTIME.search(line)
         for name, rank in EDU_RANK.items() if name in line),
        default=0
    )


def read_elite(lines):
    return any(SCHOOL.search(line) and ELITE.search(line) for line in lines)


def read_age(lines, today):
    # 简历里写的「26岁」或者出生年份；没写返回 None，不判断 JD 的年龄要求
    for line in lines:
        if m := RESUME_BIRTH.search(line):
            return today.year - int(m.group(1))
        if m := RESUME_AGE.search(line):
            return int(m.group(1))
    return None


def read_profile(lines, today):
    return {
        'edu': read_edu(lines),
        'full': read_fulltime_edu(lines),
        'elite': read_elite(lines),
        'years': read_years(lines, today),
        'age': read_age(lines, today),
    }

def edu_cut(tags, my_edu):
    if not my_edu:
        return 0
    need = max((EDU_RANK[t] for t in tags if t in EDU_RANK), default=0)
    return max(need - my_edu, 0) * 20


def field_word(text):
    # 年限要求里点名的、我没做过的领域词（「亚马逊」）；写的是我做过的领域或者没写领域，返回空
    m = OTHER_FIELD.search(text or '')
    return m.group(0) if m and not MY_FIELD.search(text or '') else ''


def years_ok(n, text, limit):
    # 求职方案写「3 年以下」时，排除最低要求达到 3 年的岗位。
    # 点名我没做过的领域（广告投放、亚马逊、AI开发…）要 2 年及以上也不符合；只要 1 年的不误伤。
    if n >= 2 and field_word(text):
        return False
    return limit is None or n < limit


def exp_cut(tags, limit, title=''):
    # 标签年限不符合（上限 3 年、标签「3-5年」；或标题是我没做过的领域、标签「1-3年」）直接扣 40：
    # 标题分到不了 60，插件也不会去读它的 JD
    for t in tags:
        m = re.fullmatch(r'(\d+)-\d+年|(\d+)年以上', t)
        if m:
            return 0 if years_ok(int(m.group(1) or m.group(2)), title, limit) else 40
    return 0


def year_limit(target, years):
    # 方案里写了经验上限就用它；没写就按简历年限：简历 2.75 年，要 3 年及以上的不符合
    if target is not None and target.max_years is not None:
        return target.max_years
    return int(years) + 1 if years is not None else None


def load_targets(saved, analysis):
    # 用户设了求职方案就用方案；没设就用简历分析推荐的方向当唯一一套
    if saved:
        return [SimpleNamespace(**{'junior': [], 'backup': [], 'max_years': None, 'min_pay': None, 'good_words': [], **t}) for t in saved]
    return [SimpleNamespace(name=None, positions=list(analysis.recommended_positions), junior=[], backup=[], max_years=None, min_pay=None, good_words=[])]


def good_hits(words, text):
    # 命中了哪些加分词（按同义说法找）
    return {w for w in words if re.search(GOOD_ALIAS.get(w, re.escape(w)), text, re.I)}

def read_active(jd):
    for line in jd.splitlines():
        if ACTIVE_LINE.fullmatch(line.strip()):
            return line.strip()
    return None


def active_ok(text):
    return text in ACTIVE_OK


def active_recent(text):
    # 「1～3日内活跃」（包括 3 日）：还在招，但比今天活跃差一点，扣分不拦
    match=re.fullmatch(r'(\d+)日内活跃',text or '')
    return bool(match and int(match.group(1)) <= 3)


def screen_pay(raw, target):
    minimum=getattr(target,'min_pay',None) if target is not None else None
    if minimum and PIECE_UNIT.search(raw or ''):
        return [PIECE_PAY],0
    pay=parse_pay_range(raw)
    if not minimum or pay is None:
        return [],0
    # 最高不超过期望、下限也没到期望（5-6K、4-7K、6-7K）：直接不打分，最多也就拿到 7K
    # 下限比期望低 1K 以上（5-15K）：直接不打分；下限在期望下方 1K 以内（6-10K）：轻扣 5 分
    # 7-7K 这种下限正好达标的放行
    floor = minimum - PAY_FLOOR_GAP
    if pay[1] < minimum or (pay[1] == minimum and pay[0] < minimum):
        return [f'{LOW_PAY}{minimum}K'],0
    if pay[0] < floor:
        return [f'{LOW_FLOOR}{floor}K'],0
    if pay[0] < minimum:
        return [f'薪资下限低于{minimum}K'],PAY_SOFT_CUT
    return [],0


def not_my_age(text, age):
    # JD 写的年龄范围不包括我：「18-25岁」「28周岁以下」
    if not age:
        return False
    m = AGE_RANGE.search(text)
    if m:
        return not int(m.group(1)) <= age <= int(m.group(2))
    m = AGE_UPPER.search(text)
    return bool(m and age > int(m.group(1)))


def senior_pay(salary):
    pay = parse_pay_range(salary) if salary else None
    return bool(pay and pay[0] >= SENIOR_PAY)


def ai_bonus_ok(jd, title, salary):
    # JD 有 AI 提效信号，且不是高薪高级岗、不是职能不对口的标题
    return bool(AI_WANT.search(jd or '')) and not senior_pay(salary) and not NON_FIT.search(title or '')


def screen_jd(jd, tags, p, title='', target=None, salary=None):
    flags, bad_years = [], []
    need_new, said_years = None, False
    service, solo, design, lead, arch, grad_soft, lang_tag = False, False, False, False, False, False, False
    lines = jd.splitlines()
    limit = year_limit(target, p['years'])
    for s in re.split(r'[。；;\n！!]', jd):
        s = LIST_NO.sub('', s)
        if not s.strip():
            continue
        # 学历、年限、外语、证书、打电话都按逗号拆开看：「2026届全日制本科，计算机专业优先」前半句仍是硬要求
        for c in re.split(r'[，,]', s):
            c = LIST_NO.sub('', c)
            if not c.strip():
                continue
            m = None if YEARS_UPPER.search(c) else (YEARS_NEED.search(c) or YEARS_AFTER.search(c))
            half = HALF_YEAR.search(c)
            said_years = said_years or bool(m or half)
            # 这条要求所在的整行，用来看旁边有没有写「应届生也可接受」
            line = next((l for l in lines if c.strip() in l), c)
            # BOSS 页面上单独一行的短标签（「团队管理经验」「27届本科」）
            tag = len(LIST_NO.sub('', line).strip()) <= 8 and not LIST_NO.match(line)
            # 「1年以上相关经验」没点名领域：领域看标题
            scope = title if RELATED.search(c) and not (OTHER_FIELD.search(c) or MY_FIELD.search(c)) else c
            if m and not YEARS_SOFT.search(c) and re.search(r'经验|开发|工作|从事', s):
                n = CN_NUM.get(m.group(1)) or int(m.group(1))
                if n <= 15 and not years_ok(n, scope, limit):
                    bad_years.append((n, field_word(scope)))
                elif n == 1 and field_word(scope) and not ACCEPT_NEW.search(line):
                    need_new = need_new or f'需1年{field_word(scope)}经验'
            if half and not YEARS_SOFT.search(c) and field_word(scope) and not ACCEPT_NEW.search(line):
                need_new = need_new or f'需半年{field_word(scope)}经验'
            if not SOFT_WORDS.search(c):
                if ELITE.search(c) and not p['elite']:
                    flags.append('要985/211')
                if re.search(r'全日制|统招', c) and re.search(r'本科|学士', c) and '大专' not in c and p['full'] < 3:
                    flags.append('要全日制本科')
                if re.search(r'硕士(及以上|以上|学历|学位)|研究生(及以上|以上|学历)', c) and not re.search(r'本科|学士|大专', c) and p['edu'] < 4:
                    flags.append('要硕士')
                if LANG.search(c):
                    # 页面上单独一行的「英语」标签先记下，正文写成要求的才压到 50
                    if tag:
                        lang_tag = True
                    else:
                        flags.append('要外语/粤语')
            # 应届生：写了届别 / 校招 / 「学历…应届毕业生」→ 只招应届；届别带「亦可/优先/接受」、「应届生优先」→ 扣分
            if not NOT_GRAD.search(c):
                if GRAD_YEAR.search(c):
                    if GRAD_OPTIONAL.search(c):
                        grad_soft = True
                    else:
                        flags.append('只招应届')
                elif GRAD_PREFER.search(c):
                    grad_soft = True
                elif (GRAD_BARE.search(c) and not tag and len(c.strip()) <= 12
                      and not GRAD_OPTIONAL.search(line) and re.search(r'学历|本科|大专|专科', line)):
                    flags.append('只招应届')
            if PREFER.search(c) or NOT_DO.search(c):
                continue
            if not_my_age(c, p.get('age')):
                flags.append('超出年龄要求')
            # 客服 / 中控：「有电商平台客服经验优先」「可接受有客服经验的」「加分项：…有客服经验」不算
            if SERVICE_JD.search(c) and not SOFT_WORDS.search(c) and not PREFER.search(line):
                service = True
            # 要能独立运营：「学习后可以独立运营店铺」「优秀者可独立负责」这种以后的事不算
            if SOLO_RUN.search(c) and not SOLO_LATER.search(s):
                solo = True
            # 剪辑 / 作图：整行写了优先、加分的不算
            if DESIGN_WORK.search(c) and not SOFT_WORDS.search(c) and not PREFER.search(line):
                design = True
            # 带团队 / 主导架构：页面标签不算，整行写了优先、「表现优秀者以后可带团队」也不算
            if not tag and not PREFER.search(line) and not LEAD_LATER.search(line):
                lead = lead or bool(TEAM_LEAD.search(c))
                arch = arch or bool(ARCH_LEAD.search(c))
            if CERT.search(c) and not CERT_TECH.search(c):
                flags.append('要证书')
            if BIG_CASE.search(c):
                flags.append('要百万级操盘案例')
            if PHONE.search(c):
                flags.append('要打电话')
    # 列表页的经验标签也算：「经验不限」没数字不影响，「3-5年」取 3；领域看标题
    for t in tags:
        m = re.fullmatch(r'(\d+)-\d+年|(\d+)年以上', t)
        if m and not years_ok(int(m.group(1) or m.group(2)), title, limit):
            bad_years.append((int(m.group(1) or m.group(2)), field_word(title)))
        # 标签「1-3年」、标题是我没做过的领域：JD 自己没写年限、也没说接受新人，才按标签扣分
        elif m and int(m.group(1) or m.group(2)) == 1 and field_word(title) and not said_years and not ACCEPT_NEW.search(jd):
            need_new = need_new or f'需1年{field_word(title)}经验'
    if LANG.search(title or ''):
        flags.append('要外语/粤语')
    # 标题写了届别：「27届」压到 50；「26应届小白可来」这种扣分
    if GRAD_YEAR.search(title or '') and not NOT_GRAD.search(title):
        if GRAD_OPTIONAL.search(title) or re.search(r'小白|可来', title):
            grad_soft = True
        else:
            flags.append('只招应届')
    # 本地生活是我做过的：这类岗位写「不接受小白」「要独立运营」我也符合
    local = LOCAL_LIFE.search(title or '') or LOCAL_LIFE.search(jd)
    if service or (SERVICE_TITLE.search(title or '') and not AI_SERVICE.search(title or '')):
        flags.append('偏客服/中控')
    if REJECT_NEW.search(jd) and not local:
        flags.append('不收新手')
    if solo and not local:
        flags.append('要独立运营经验')
    if design:
        flags.append('偏剪辑/设计')
    if lead:
        flags.append('要带团队')
    if arch:
        flags.append('要主导架构设计')
    # 年限不符合：上限 3 年时，最低要求达到 3 年才不行。
    new_cut = 0
    if bad_years:
        n, word = max(bad_years)
        flags.append(f'要{n}年{word}经验')
    elif need_new:
        flags.append(need_new)
        new_cut = need_new_cut(need_new, title, salary, target)
    # 「降低获客成本」是考核指标，「抖音本地推」是投放工具，「接受无商家拓展经验」是 BOSS 标签：先删掉再判断
    text = NOT_SALES.sub('', jd)
    strong = any(STRONG_SALES.search(l) and not PREFER.search(l) and not NOT_DO.search(l) for l in text.splitlines())
    if strong or (any(w in text for w in SALES_DO) and any(w in text for w in SALES_PAY)):
        flags.append('疑似销售岗')
    # 技术支持 / 实施类：硬件词 3 种以上，或 2 种且比软件词多，算硬件设备支持
    hw = len({w.lower() for w in HW_WORDS.findall(jd)})
    sw = len({w.lower() for w in SW_WORDS.findall(jd)})
    # 标题就是设备调试 / 安装调试：车间现场活
    if (any(w in jd for w in FIELD_WORDS) or HW_TITLE.search(title or '')
            or (SUPPORT_TITLE.search(title) and (hw >= 3 or (hw >= 2 and sw < hw)))):
        flags.append('偏硬件/现场')
    has_ai, has_auto = bool(AI_TOOL.search(jd)), bool(AUTO_TOOL.search(jd))
    if CONTENT_TITLE.search(title) and not (has_ai or has_auto):
        flags.append('内容岗没要求AI工具')
    if dev_lang_miss(title, jd):
        flags.append(DEV_LANG_FLAG)
    if CORE_MODEL_RISK.search(jd):
        flags.append('偏算法/模型训练')
    if LARGE_PROJECT_RISK.search(jd):
        flags.append('需独立负责大型项目')
    if ADVANCED_INFRA_RISK.search(jd):
        flags.append('偏高级基础设施')
    active = read_active(jd)
    recent_cut = 0
    if active and not active_ok(active):
        if active_recent(active):
            flags.append(f'HR{active}')
            recent_cut = HR_RECENT_CUT
        else:
            flags.append(f'{STALE_HR}（{active}）')
    flags = list(dict.fromkeys(flags))
    # 加分用负的扣分表示。不同能力项累加，同一项的同义词只计一次，最多加 30 分。
    _,points=requirement_hits(jd)
    fit=min(points,30)
    # 加分词：标题和标签里已经加过的不重复加，合起来最多 10 分
    words = target.good_words if target is not None else []
    seen = good_hits(words, title + ' ' + ' '.join(tags))
    good = min(len(good_hits(words, jd) | seen) * GOOD_EACH, GOOD_MAX) - min(len(seen) * GOOD_EACH, GOOD_MAX)
    # 面向应届生（届别写了亦可 / 优先，或应届生优先）：没被判只招应届的，扣 10 分
    grad_cut = 0
    if grad_soft and '只招应届' not in flags:
        flags.append(GRAD_SOFT)
        grad_cut = GRAD_CUT
    # 英语只挂在页面标签上：扣 10 分，不压到 50（跨境岗日常多半还是要用英语）
    lang_cut = 0
    if lang_tag and '要外语/粤语' not in flags:
        flags.append(LANG_TAG_FLAG)
        lang_cut = LANG_TAG_CUT
    # 公司想用 AI 提效 / 接入 AI：+10
    ai_bonus = AI_BONUS if ai_bonus_ok(jd, title, salary) else 0
    cut = -fit - good + recent_cut + new_cut + grad_cut + lang_cut - ai_bonus
    return flags, cut


# 「需1年X经验」「需半年X经验」：只要 1 年及以内没做过领域的经验
NEED_NEW = ('需1年', '需半年')


def need_new_cut(flag, title, salary, target):
    # 要 1 年及以内（含 1 年）的不扣分（用户：一年或一年内都可以）；
    # 工资下限≥15K（多半是高级岗）、职能不对口的标题照旧扣，标题对上方向的少扣一半
    if not flag.startswith(NEED_NEW) or not (senior_pay(salary) or NON_FIT.search(title or '')):
        return 0
    positions = list(getattr(target, 'positions', [])) + list(getattr(target, 'junior', []))
    rule = bool(positions) and title_rule_match(title, positions) is True
    return NEW_FIELD_CUT - NEW_FIELD_EASE * int(rule)


def flag_note(flag, title, salary, target):
    # 岗位池上「不合适」的标签：后面注明这一条对分数的影响
    if flag.startswith((STALE_HR, LOW_PAY, LOW_FLOOR, PIECE_PAY)):
        return f'{flag}（0分）'
    if is_hard(flag):
        return f'{flag}（最高{HARD_CAP}）'
    if flag.startswith('薪资下限低于'):
        return f'{flag}（-{PAY_SOFT_CUT}）'
    if flag.startswith('HR'):
        return f'{flag}（-{HR_RECENT_CUT}）'
    if flag == GRAD_SOFT:
        return f'{flag}（-{GRAD_CUT}）'
    if flag == LANG_TAG_FLAG:
        return f'{flag}（-{LANG_TAG_CUT}）'
    if flag.startswith(NEED_NEW):
        cut = need_new_cut(flag, title, salary, target)
        return f'{flag}（-{cut}）' if cut else f'{flag}（不扣分）'
    return flag


def required_text(jd):
    # JD 里的硬要求：「加分项」小标题后面的行、写了优先 / 加分的行都不算
    out, bonus = [], False
    for line in (jd or '').splitlines():
        s = LIST_NO.sub('', line).strip()
        if BONUS_HEAD.match(s):
            bonus = True
            continue
        if SECTION_HEAD.match(s):
            bonus = False
        if not bonus and not PREFER.search(s):
            out.append(s)
    return '\n'.join(out)


def dev_lang_miss(title, jd):
    # 开发岗用的语言不是 Python / JS：标题写明 C++ / Java / Go…又没写 Python、JS，直接算；
    # 否则看 JD 的硬要求部分有没有 Python / JS（只在加分项里提一句 Python 不算）；前端、全栈岗本来就写 JS，不按 JD 判断
    t = NOT_DEV_WORDS.sub('', title or '')
    if not DEV_TITLE.search(t):
        return False
    if TITLE_LANG.search(t) and not MY_LANG.search(t):
        return True
    if re.search(r'前端|全栈|web', t, re.I):
        return False
    return bool(OTHER_LANG.search(jd or '') and not MY_LANG.search(t + '\n' + required_text(jd)))


def mentor_ok(jd):
    # 有一行写了有人带这类、而且不是「负责带教别人」
    return any(MENTOR.search(line) and not MENTOR_NOT.search(line) for line in (jd or '').splitlines())


def is_hard(flag):
    return flag in HARD_FLAGS or flag.startswith(LOW_PAY) or bool(re.match(r'要\d+年', flag))


def apply_jd(base, flags, cut):
    if not base:
        return 0
    # HR 超过 3 天没活跃、工资最高不超过期望：直接 0 分
    if any(f.startswith((STALE_HR, LOW_PAY, LOW_FLOOR, PIECE_PAY)) for f in flags):
        return 0
    if any(is_hard(f) for f in flags):
        return min(max(base - max(cut, 0), 0), HARD_CAP)
    return min(max(base - cut, 0), 100)

def quick_score(analysis, jobs, edu=0, years=None, target=None):
    t = target or load_targets(None, analysis)[0]
    names = [job.name for job in jobs]
    positions = list(t.positions) + list(t.junior)
    vecs = embed_many(names + positions + list(AVOID_ROLES))
    avoids = [
        a for a in AVOID_ROLES
        if max((dot(vecs[a], vecs[p]) for p in positions if a in vecs and p in vecs), default=0.0) < OVERLAP
    ]
    # 方案里本身有技术岗方向（比如「软件实施工程师」），就不拦技术岗标题
    block_tech = not any(TECH_TITLE.search(p) for p in positions)
    limit = year_limit(t, years)
    items = []
    for job in jobs:
        # 先去掉空格：「AI 软 件 销 售 助 理」这种写法能绕过拦截词
        title = re.sub(r'\s+', '', job.name.lower())
        ops = any(w in title for w in RESCUE_WORDS)
        block_title = BOSS_ASSIST.sub('助理', title)
        block_word = next((
            w for w in BLOCK_WORDS
            if w.lower() in block_title and not (ops and w in LOOSE_BLOCK)
        ), None)
        rule_match=title_rule_match(job.name,positions)
        pay_flags, pay_cut = screen_pay(getattr(job, 'salary', None), t)
        hard_year = next((
            int(m.group(1) or m.group(2))
            for tag in job.tags
            if (m := re.fullmatch(r'(\d+)-\d+年|(\d+)年以上', tag))
            and not years_ok(int(m.group(1) or m.group(2)), job.name, limit)
        ), None)
        if block_word:
            items.append(QuickScoreItem(
                name=job.name, score=0, matched=[], read_jd=False, screen='skip',
                reason=f'标题含排除词「{block_word}」'
            ))
            continue
        if MANAGER_TITLE.search(title) and not JUNIOR_ROLE.search(title):
            items.append(QuickScoreItem(
                name=job.name, score=0, matched=[], read_jd=False, screen='skip',
                reason='管理岗（主管/经理/店长）'
            ))
            continue
        if hard_year is not None:
            items.append(QuickScoreItem(
                name=job.name, score=0, matched=[], read_jd=False, screen='skip',
                reason=f'经验标签从{hard_year}年起'
            ))
            continue
        # 工资最高不超过期望（4-7K）：不打分，插件也不去读 JD
        if pay_flags and pay_flags[0].startswith((LOW_PAY, LOW_FLOOR, PIECE_PAY)):
            items.append(QuickScoreItem(
                name=job.name, score=0, matched=[], read_jd=False, screen='skip',
                reason=pay_flags[0]
            ))
            continue
        if block_tech and TECH_TITLE.search(title) and not OPS_ROLE.search(title):
            items.append(QuickScoreItem(
                name=job.name, score=0, matched=[], read_jd=False, screen='skip',
                reason='技术岗位不在当前求职方向'
            ))
            continue
        if DEV_TITLE.search(title) and rule_match is False and not TARGET_DEV.search(title):
            items.append(QuickScoreItem(
                name=job.name, score=0, matched=[], read_jd=False, screen='skip',
                reason='开发方向明显不符'
            ))
            continue

        jv = vecs.get(job.name)
        sims = {p: dot(jv, vecs[p]) for p in positions if jv and p in vecs}
        want = max(sims.values(), default=0.0)
        avoid = max((dot(jv, vecs[p]) for p in avoids if jv and p in vecs), default=0.0)

        best = max(sims, key=sims.get) if sims else ''
        # 最像的是「只投初级」的方向，标题又不是初级 / 助理岗，不要
        junior_miss = best in t.junior and not (JUNIOR.search(title) or any('应届' in g for g in job.tags))
        # 开发类标题，最像的方向也得是开发 / 自动化方向才算
        dev_miss = DEV_TITLE.search(title) and not OPS_ROLE.search(title) and not DEV_DIR.search(best)
        # 跟要避开的方向更像 —— 不是我要的岗位；运营类标题（又不是技术岗）跳过这一步
        rescued = ops and not TECH_TITLE.search(title)
        uncertain = rule_match is not True and (
            junior_miss or dev_miss or (not rescued and avoid + AVOID_MARGIN > want)
        )

        # 标题只负责确认方向，最高 70 分；不能再仅靠标题和少量标签冲到 100 分。
        # 标题只用来初筛：对上方向的优先读 JD，但不再给保底分，分数由 JD 里的实际职责决定
        base = min(round(want * 70),70) if want >= 0.5 else 0
        if not base:
            # 没有明显排除特征的岗位保留候选分，让 JD 有机会证明它相关。
            base = 20
        if uncertain:
            base = min(base, 35)
        real_tags = [g for g in job.tags if not SKIP_TAG.search(g)]
        skill = calculate_skill_score(analysis.skills, real_tags)
        bonus = min(len(skill.matched_skills), 2) * 5
        # 标题和标签里的加分词（经验不限、助理……），标题本身对得上才加
        title_good = good_hits(t.good_words, title + ' ' + ' '.join(job.tags))
        good = min(len(title_good) * GOOD_EACH, GOOD_MAX) if base else 0
        total = min(100, base + bonus + good)
        cut_edu, cut_exp = edu_cut(job.tags, edu), exp_cut(job.tags, limit, job.name)
        if total:
            total = max(total - cut_edu - cut_exp, 0)
        # 标题只是写法不完全匹配时先压到55分，JD证据足够后仍可达标。
        if rule_match is False:
            total = min(total, 55)
        total = max(total - pay_cut, 0)
        # 岗位池上显示的合适 / 不合适的点（工资的在 score_jobs 里跟 JD 门槛一起列）
        dirs = [p for p in positions if title_rule_match(job.name, [p]) is True]
        pros, cons = [], []
        if dirs:
            pros.append(f'方向对上：{"、".join(dirs[:2])}')
        elif rule_match is None and best and want >= 0.5 and not uncertain:
            pros.append(f'标题接近：{best}')
        if uncertain:
            cons.append('标题和求职方向不太像（标题分最高35）')
        elif rule_match is False:
            cons.append('标题不在求职方向里（标题分最高55）')
        pay = parse_pay_range(getattr(job, 'salary', None))
        if pay and t.min_pay and pay[0] >= t.min_pay:
            pros.append(f'工资达标（≥{t.min_pay}K）')
        edu_tags = sorted((g for g in job.tags if g in EDU_RANK), key=EDU_RANK.get)
        if cut_edu:
            cons.append(f'学历要{edu_tags[-1]}，高于你（-{cut_edu}）')
        elif edu and (edu_tags or '学历不限' in job.tags):
            pros.append(f'学历符合（{edu_tags[-1] if edu_tags else "学历不限"}）')
        year_tag = next((g for g in job.tags if re.fullmatch(r'\d+-\d+年|\d+年以上|\d+年以内', g)), None)
        if cut_exp:
            cons.append(f'经验要{year_tag}（-{cut_exp}）')
        elif year_tag:
            pros.append(f'经验要求符合（{year_tag}）')
        pros += [w for w in t.good_words if w in title_good]
        if '经验不限' in job.tags:
            pros.append('经验不限')
        if skill.matched_skills:
            pros.append(f'标签技能：{"、".join(skill.matched_skills[:3])}')
        # 备选方向的岗位排在主投后面：只对上备选方向就扣 5 分
        backup = set(getattr(t, 'backup', []) or [])
        if backup:
            hit = dirs or ([best] if best else [])
            if hit and all(p in backup for p in hit):
                total = max(total - BACKUP_CUT, 0)
                cons.append(f'备选方向（-{BACKUP_CUT}）')
        items.append(QuickScoreItem(
            name=job.name, score=total, matched=skill.matched_skills,
            screen='priority' if rule_match is True else 'review',
            reason='标题符合，优先读取JD' if rule_match is True else '标题模糊，由JD确认',
            pros=list(dict.fromkeys(pros)), cons=cons,
        ))
    return items


def score_jobs(analysis, targets, jobs, profile):
    # 每套求职方案各打一次分（标题分；读过 JD 再算门槛和加分），留分最高的那套，一样高看标题分
    best = [None] * len(jobs)
    screen_rank = {'skip': 0, 'review': 1, 'priority': 2}
    screens = ['skip'] * len(jobs)
    for t in targets:
        items = quick_score(analysis, jobs, profile['edu'], profile['years'], t)
        for i, (job, it) in enumerate(zip(jobs, items)):
            if screen_rank[it.screen] > screen_rank[screens[i]]:
                screens[i] = it.screen
            # BOSS 的 JD 里夹着长得像汉字的部首字，先换回普通字再判断
            jd = plain_text(getattr(job, 'jd', None))
            jd_flags, jd_cut = screen_jd(jd, job.tags, profile, job.name, t, getattr(job, 'salary', None)) if jd else ([], 0)
            jd_hits,_ = requirement_hits(jd) if jd else ([],0)
            if jd and ai_bonus_ok(jd, job.name, getattr(job, 'salary', None)):
                jd_hits = list(jd_hits) + [AI_HIT]
            # 工资的 5 分在标题分里已经扣过，这里只带上标签，不再重复扣
            pay_flags, _ = screen_pay(getattr(job,'salary',None),t)
            flags=list(dict.fromkeys(pay_flags+jd_flags))
            cut=jd_cut
            score=apply_jd(it.score,flags,cut)
            # 合适的点：标题阶段的 + JD 里的（HR 活跃、加分词、能力项、AI 提效）
            pros = list(it.pros)
            if jd:
                active = read_active(jd)
                if active and active_ok(active):
                    pros.append(f'HR{active}')
                seen = good_hits(t.good_words, job.name + ' ' + ' '.join(job.tags))
                jd_good = good_hits(t.good_words, jd)
                pros += [w for w in t.good_words if w in jd_good and w not in seen]
                pros += [h for h in jd_hits if h != AI_HIT]
                if AI_HIT in jd_hits:
                    pros.append(f'{AI_HIT}（+{AI_BONUS}）')
            # 只要 1 年及以内的经验、又不扣分的，算合适（用户：一年或一年内都可以）；高薪岗、职能不对口扣了分的才算不合适
            easy = [f for f in flags if f.startswith(NEED_NEW) and not need_new_cut(f, job.name, getattr(job, 'salary', None), t)]
            pros += ['只要' + f[1:] for f in easy]
            # 不合适的点：标题阶段就判 0 分的写原因；JD 门槛、工资、HR 注明扣多少
            cons = [f'{it.reason}（0分）'] if not it.read_jd else list(it.cons)
            cons += [flag_note(f, job.name, getattr(job, 'salary', None), t) for f in flags
                     if (it.read_jd or f != it.reason) and f not in easy]
            # 有人带的岗位：没踩硬门槛、没有扣分的「需1年X经验」、不是面向应届生、工资和 HR 没问题，至少 60 分
            if (jd and 0 < score < MENTOR_FLOOR and it.score >= MENTOR_TITLE_MIN and mentor_ok(jd)
                    and not any(is_hard(f) for f in flags)
                    and not any(f.startswith(NEED_NEW) and f not in easy for f in flags)
                    and not any(f.startswith((GRAD_SOFT, STALE_HR, LOW_PAY, LOW_FLOOR, PIECE_PAY)) for f in flags)):
                score = MENTOR_FLOOR
                jd_hits = list(jd_hits) + [MENTOR_HIT]
                pros.append(f'{MENTOR_HIT}（保底{MENTOR_FLOOR}）')
            if best[i] is None or (it.read_jd, score, it.score) > (
                best[i]['read_jd'], best[i]['score'], best[i]['base']
            ):
                best[i] = {
                    'target': t.name, 'base': it.score, 'flags': flags, 'cut': cut,
                    'score': score, 'matched': it.matched, 'hits': jd_hits,
                    'read_jd': it.read_jd, 'reason': it.reason,
                    'pros': list(dict.fromkeys(pros)), 'cons': list(dict.fromkeys(cons)),
                }
    for item,screen in zip(best,screens):
        item['screen']=screen
    return best
