import re


# 【这部分可以AI生成，不要求背】
# JD命中项与简历证据使用不同词表。这里刻意采用更严格的证明标准。
PROOF_RULES = {
    'Python': r'python',
    'Web框架': r'fastapi|flask|django',
    'SQL/数据库': r'(?<![a-z])sql(?![a-z])|mysql|sqlite|sqlalchemy|数据库',
    'API/接口': r'(?<![a-z])api(?![a-z])|restful?|接口(?:开发|调用|对接|联调)',
    'RAG/知识库': r'(?<![a-z])rag(?![a-z])|知识库|embedding|向量检索',
    'Agent/工具调用': r'(?<![a-z])agent(?![a-z])|tool\s*calling|function\s*calling|工具调用',
    '大模型API/Prompt': r'大模型\s*api|prompt|提示词|结构化输出|模型接口',
    'Vue/前端': r'(?<![a-z])vue(?:\s*3)?(?![a-z])|javascript|html|css|axios|前端',
    'Git': r'(?<![a-z])git(?:hub)?(?![a-z])',
    'Redis': r'(?<![a-z])redis(?![a-z])',
    'Docker/Linux部署': r'docker(?:\s*compose)?|linux|nginx|部署|上线',
    'Excel/Pandas': r'excel|pandas|数据透视表',
    '数据分析/报表': r'数据分析|数据清洗|数据处理|数据统计|报表|复盘',
    '需求分析/方案': r'需求(?:调研|分析|梳理|拆解)|方案设计|解决方案',
    'AI实施/交付': r'(?:ai|人工智能|大模型|智能体).{0,8}(?:实施|交付|落地)|客户培训|用户培训|数据导入|系统集成',
    'RPA/业务自动化': r'(?<![a-z])rpa(?![a-z])|影刀|uibot|uipath|power\s*automate|selenium|playwright|浏览器自动化|流程自动化|业务自动化|自动化脚本',
    'AI工具/低代码': r'dify|coze|扣子|n8n|langchain|llamaindex|低代码',
    'SaaS/ERP实施': r'(?<![a-z])saas(?![a-z])|(?<![a-z])erp(?![a-z])|(?<![a-z])crm(?![a-z])|系统实施|软件实施',
    '跨境电商经验': r'跨境电商|amazon|亚马逊|tiktok\s*shop|temu|shopee|lazada|ebay|独立站',
    '电商平台/运营': r'跨境电商|电商运营|店铺运营|amazon|亚马逊|tiktok|抖音|temu|shopee|独立站',
    '库存/仓储经验': r'库存(?:管理|盘点|预警|周转|同步)?|仓储|仓库|(?<![a-z])wms(?![a-z])',
    '商品/订单/库存': r'商品上架|listing|订单|库存|仓储|物流|sku|商品',
    '广告投放/数据指标': r'广告投放|信息流|付费推广|roi|roas|cpa|cpc|ctr|cvr|转化率',
    '个人项目/作品': r'个人项目|github|作品集|作品展示|(?<![a-z])demo(?![a-z])|(?<![a-z])poc(?![a-z])',
}

def compare_proofs(hits:list[str], proofs:list[dict])->dict:
    matched = []
    missing = []
    for name in hits:
        rule = PROOF_RULES.get(name)
        if not rule:
            continue
        found = [p for p in proofs if (
            name == '个人项目/作品' and p.get('source') == 'project'
        ) or re.search(rule, p.get('text',''), re.I)]
        if found:
            matched.append({'name':name, 'proofs':found})
        else:
            missing.append(name)
    return {'matched':matched, 'missing':missing}
