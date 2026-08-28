from app.services import ai_resume_service as ai_resume

def test_resume_fail(monkeypatch):
#    monkeypatch 临时替换程序里面某个东西。测试结束后自动恢复。
    monkeypatch.setattr(ai_resume.settings,'llm_mock_mode', False)
    monkeypatch.setattr(ai_resume.settings,'llm_model','test-model')
    def fail():
        raise RuntimeError('模拟故障')
    monkeypatch.setattr(ai_resume,'get_llm_client',fail)
    res=ai_resume.analyze_resume_with_ai(1,'测试简历')
    assert res.ai_ok is False

def test_parse_fail(monkeypatch):
    monkeypatch.setattr(ai_resume.settings,'llm_mock_mode',False)
    monkeypatch.setattr(ai_resume.settings,'llm_model','test-model')

    class FakeRes:
        def parse(self,**kwargs):
# **kwargs：【语言固定语法】接收调用时传进来的全部命名参数；【不用背，知道用途即可】。
            raise RuntimeError('模拟请求故障')
    class FakeClient:
        responses=FakeRes()
    def fake_client():
        return FakeClient()
    monkeypatch.setattr(ai_resume,'get_llm_client',fake_client)
    res=ai_resume.analyze_resume_with_ai(1,'测试简历')
    assert res.ai_ok is False

# 公司系统不能因为 AI 返回空数据就崩溃。
def test_empty(monkeypatch):
    monkeypatch.setattr(ai_resume.settings,'llm_mock_mode',False)
    monkeypatch.setattr(ai_resume.settings,'llm_model','test-model')
    class Empty:
        output_parsed=None
    class FakeRes:
        def parse(self,**kwargs):
            return Empty()
    class FakeClient:
        responses=FakeRes()
    def fake_client():
        return FakeClient()
    monkeypatch.setattr(ai_resume,'get_llm_client',fake_client)
    res=ai_resume.analyze_resume_with_ai(1,'测试简历')
    assert res.ai_ok is False