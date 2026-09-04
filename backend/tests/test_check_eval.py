import os
import pytest
from app.schemas import Need, Needs
from app.services.job_assist_service import get_checks

@pytest.mark.skipif(
    os.getenv('RUN_AI_EVAL') != '1',
    reason='真实模型评测，默认跳过，避免产生费用'
)
def test_work_not_personality():
    needs = Needs(items=[
        Need(id=0, text='客观认识自己，具有平常心者优先',
             kind='加分', quote='客观认识自己，具有平常心者优先')
    ])
    proofs = ['负责门店运营。', '使用JavaScript开发展示页面。', '正在学习Python。']
    result = get_checks(needs, proofs)
    item = result.items[0]
    assert item.status == '未找到依据', item.model_dump()
    assert item.proof_ids == [], item.model_dump()