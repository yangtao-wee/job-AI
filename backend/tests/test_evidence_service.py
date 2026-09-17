from app.services.evidence_service import compare_proofs


def test_workflow_test_is_not_requirement_analysis():
    proofs = [{"id": "W8", "text": "编写自动化测试，覆盖主要业务流程"}]

    result = compare_proofs(["需求分析/方案"], proofs)

    assert result == {"matched": [], "missing": ["需求分析/方案"]}


def test_using_ai_tool_is_not_low_code_experience():
    proofs = [{"id": "W14", "text": "使用AI工具辅助活动文案和短视频内容生产"}]

    result = compare_proofs(["AI工具/低代码"], proofs)

    assert result == {"matched": [], "missing": ["AI工具/低代码"]}


def test_domestic_douyin_is_not_cross_border_experience():
    proofs = [{"id": "W10", "text": "负责抖音本地生活店铺运营"}]

    result = compare_proofs(["跨境电商经验"], proofs)

    assert result == {"matched": [], "missing": ["跨境电商经验"]}


def test_order_experience_is_not_inventory_experience():
    proofs = [{"id": "W11", "text": "根据订单、核销和评分数据持续复盘"}]

    result = compare_proofs(["库存/仓储经验"], proofs)

    assert result == {"matched": [], "missing": ["库存/仓储经验"]}


def test_project_source_proves_personal_project():
    proofs = [{"id": "P1", "text": "使用FastAPI与Agent开发求职助手", "source": "project"}]

    result = compare_proofs(["个人项目/作品"], proofs)

    assert result["matched"][0]["proofs"] == proofs
