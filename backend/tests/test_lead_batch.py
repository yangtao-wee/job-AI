from types import SimpleNamespace as NS
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.main import app
from app.dependencies import get_current_user,get_db
from app.models import Base,JobLead
from app.routers import leads
from app.schemas import LeadIn
from app.services import lead_service
from app.services.matching_service import load_targets

client=TestClient(app)


def test_upload_leads_passes_score_context(monkeypatch):
    app.dependency_overrides[get_current_user]=lambda:NS(id=7)
    app.dependency_overrides[get_db]=lambda:object()
    seen={}
    monkeypatch.setattr(leads,'score_context',lambda db,user,rid:{'rid':rid})

    def fake_save(db,user_id,items,ctx):
        seen.update(user_id=user_id,n=len(items),ctx=ctx)
        return {'added':1,'updated':0,'total':1}

    monkeypatch.setattr(leads,'save_leads',fake_save)
    try:
        body={'leads':[{'title':'电商运营助理','url':'u1','salary':'8-12K'}],'resume_id':9}
        assert client.post('/leads/batch',json=body).status_code==200
        assert seen=={'user_id':7,'n':1,'ctx':{'rid':9}}
        # 旧插件不带简历编号也能入库
        assert client.post('/leads/batch',json={'leads':[{'title':'电商运营助理','url':'u1'}]}).status_code==200
        assert seen['ctx'] is None
    finally:
        app.dependency_overrides.clear()


def test_save_leads_rescores_with_salary(monkeypatch):
    monkeypatch.setattr('app.services.matching_service.embed_many',lambda texts:{t:[1.0,0.0] for t in texts})
    analysis=NS(skills=[],recommended_positions=[])
    targets=load_targets([{'name':'B','positions':['电商运营'],'max_years':3,'min_pay':7}],analysis)
    ctx={'analysis':analysis,'targets':targets,'profile':{'edu':3,'full':2,'elite':False,'years':2.75}}
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        lead_service.save_leads(db,1,[LeadIn(title='电商运营助理',url='u1',salary='6-8K',quick_score=70)],ctx)
        row=db.query(JobLead).one()
        # 6-8K 跨过 7K，只轻扣 5 分；没读 JD 的岗位最高 54 分。
        assert (row.quick_score,row.jd_flags)==(54,['薪资下限低于7K'])
        # 下一次插件没读到工资：不清掉原来的工资
        lead_service.save_leads(db,1,[LeadIn(title='电商运营助理',url='u1',quick_score=70)],ctx)
        db.refresh(row)
        assert row.salary=='6-8K'
