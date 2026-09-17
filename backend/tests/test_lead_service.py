from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from unittest.mock import MagicMock
import pytest
from app.models import Base, JobLead
from app.services.lead_service import update_status, save_leads, mark_above,unmark_all
from app.schemas import LeadIn, LeadJdIn
from app.services import lead_service as service
from app.services.matching_service import load_targets
from types import SimpleNamespace

def test_update_status_isolated():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        lead = JobLead(user_id=1, title='Python', company='A', url='https://test/1')
        db.add(lead); db.commit(); db.refresh(lead)
        assert update_status(db, 2, lead.id, '已投递') is None
        db.refresh(lead)
        assert lead.status == '新抓取'
        assert update_status(db, 1, lead.id, '已投递').status == '已投递'

def test_update_status_rolls_back():
    db = MagicMock()
    lead = MagicMock(status='新抓取')
    db.query.return_value.filter.return_value.first.return_value = lead
    db.commit.side_effect = SQLAlchemyError('commit failed')

    with pytest.raises(SQLAlchemyError):
        update_status(db, 1, 1, '已投递')

    db.rollback.assert_called_once()
    db.refresh.assert_not_called()

def test_save_leads_is_idempotent():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        first = LeadIn(title='Python', company='A', url='https://test/1', salary='6-8K', quick_score=60)
        higher = LeadIn(title='Python', company='A', url='https://test/1', salary='7-10K', quick_score=80)

        assert save_leads(db, 1, [first]) == {'added': 1, 'updated': 0, 'total': 1, 'has_jd': []}
        assert save_leads(db, 1, [higher]) == {'added': 0, 'updated': 1, 'total': 1, 'has_jd': []}
        rows = db.query(JobLead).all()
        assert len(rows) == 1
        # 没读过 JD：标题分记在 base_score，展示分最高 59
        # 标题分 80，但没读 JD，最高 54
    assert (rows[0].base_score, rows[0].quick_score, rows[0].salary) == (80, 54, '7-10K')

def test_analyze_next_keeps_one_transaction(monkeypatch):
    db=MagicMock()
    base=db.query.return_value.filter.return_value
    job=MagicMock(
        jd_text='负责Python后端、AI应用工程和系统稳定性建设工作。',
        title='Python开发',company='A'
    )
    base.order_by.return_value.first.return_value=job
    result=MagicMock(checks=[])
    monkeypatch.setattr(service,'make_report',lambda *args:result)
    save=MagicMock(return_value=MagicMock(id=9))
    monkeypatch.setattr(service,'save_report',save)
    service.analyze_next(db,1,2,['proof'])
    assert save.call_args.kwargs['commit'] is False
    assert job.report_id==9
    db.commit.assert_called_once()

def make_db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return Session(engine)

def test_list_leads_filters_and_pages():
    with make_db() as db:
        db.add_all([
            JobLead(user_id=1,title='高分',url='u1',quick_score=90,status='待投递'),
            JobLead(user_id=1,title='中分',url='u2',quick_score=60,status='待投递'),
            JobLead(user_id=1,title='其他状态',url='u3',quick_score=100),
            JobLead(user_id=2,title='其他用户',url='u4',quick_score=95,status='待投递'),
        ])
        db.commit()

        rows,total,_=service.list_leads(db,1,'待投递',1,1)
        assert total==2
        assert [row.title for row in rows]==['中分']


def test_lead_out_shows_readable_salary():
    from datetime import datetime
    from app.schemas import LeadOut
    now=datetime(2026,9,17)
    row=dict(id=1,title='跨境电商运营',company='A',url='u',tags=[],quick_score=73,deep_ok=0,deep_part=0,
             deep_total=0,status='新抓取',created_at=now,updated_at=now)
    assert LeadOut.model_validate(dict(row,salary='\ue032\ue036-\ue033\ue031K')).salary=='15-20K'
    assert LeadOut.model_validate(dict(row,salary=None)).salary is None


def test_unread_jd_skips_zero_read_applied_and_skipped():
    with make_db() as db:
        db.add_all([
            JobLead(user_id=1,title='待读高分',url='u1',quick_score=54),
            JobLead(user_id=1,title='待读低分',url='u2',quick_score=30),
            JobLead(user_id=1,title='标题判0分',url='u3',quick_score=0),
            JobLead(user_id=1,title='读过了',url='u4',quick_score=54,jd_text='x'*30),
            JobLead(user_id=1,title='投过了',url='u5',quick_score=54,status='已投递'),
            JobLead(user_id=1,title='跳过了',url='u6',quick_score=54,status='已跳过'),
            JobLead(user_id=2,title='别人的',url='u7',quick_score=54),
        ])
        db.commit()
        result=service.list_unread_jd(db,1,1)
        assert result['total']==2
        assert [row.url for row in result['items']]==['u1']
        assert service.lead_stats(db,1)['unread_jd']==2


def test_lead_kinds_by_title():
    assert service.lead_kinds('跨境电商运营助理')==['跨境电商']
    assert service.lead_kinds('Tik Tok运营专员')==['跨境电商']
    assert service.lead_kinds('国内电商运营（拼多多）')==['国内电商']
    assert service.lead_kinds('AI Agent 应用开发工程师（跨境电商）')==['跨境电商','AI相关','自动化/开发']
    assert service.lead_kinds('Facebook广告投放')==['广告投放']
    assert service.lead_kinds('本地生活运营 美团大众点评')==['本地生活']
    assert service.lead_kinds('软件实施工程师')==['实施/技术支持']
    # 销售只算销售；产品开发不是写代码；哪类都不沾的运营岗算「其他运营」
    assert service.lead_kinds('AI/Saas软件销售顾问')==['销售/业务']
    assert service.lead_kinds('产品开发助理')==['其他']
    assert service.lead_kinds('新媒体运营')==['其他运营']
    assert service.lead_kinds('天猫运营助理/售前售后客服')==['国内电商']


def test_list_leads_search_kind_and_tier():
    with make_db() as db:
        db.add_all([
            JobLead(user_id=1,title='亚马逊运营助理',company='甲公司',url='u1',quick_score=70,jd_text='负责店铺，有人带'),
            JobLead(user_id=1,title='跨境电商运营',company='乙公司',url='u2',quick_score=56,jd_text='要英语'),
            JobLead(user_id=1,title='AI应用开发',company='丙公司',url='u3',quick_score=50),
            JobLead(user_id=1,title='电商运营助理',company='亚马逊合作方',url='u4',quick_score=40,jd_text='双休'),
            JobLead(user_id=2,title='亚马逊运营助理',company='别人的',url='u5',quick_score=90,jd_text='x'),
        ])
        db.commit()

        rows,total,facets=service.list_leads(db,1,keyword='亚马逊')
        assert total==2
        assert [row.url for row in rows]==['u1','u4']
        assert facets['kinds']['跨境电商']==1 and facets['kinds']['国内电商']==1

        rows,total,_=service.list_leads(db,1,keyword='亚马逊 助理 有人带',in_jd=True)
        assert [row.url for row in rows]==['u1']

        rows,total,facets=service.list_leads(db,1,kind='跨境电商')
        assert [row.url for row in rows]==['u1','u2']
        assert facets['tiers']=={'全部':2,'建议投':1,'可投可不投':1,'待读JD':0,'先不看':0}
        assert facets['kinds']['全部']==4

        rows,total,facets=service.list_leads(db,1,tier='待读JD')
        assert [row.url for row in rows]==['u3']
        assert facets['kinds']['AI相关']==1 and facets['kinds']['跨境电商']==0

        # 搜索词里的 % 不能当通配符
        assert service.list_leads(db,1,keyword='%')[1]==0


def test_mark_above_includes_skipped():
    with make_db() as db:
        db.add_all([
            JobLead(user_id=1, title='高分', url='u1', quick_score=80),
            JobLead(user_id=1, title='刚好', url='u2', quick_score=60),
            JobLead(user_id=1, title='低分', url='u3', quick_score=30),
            JobLead(user_id=1, title='已跳过的高分', url='u4',
                    quick_score=90, status='已跳过'),
            JobLead(user_id=1, title='已投递的高分', url='u6',
                    quick_score=85, status='已投递'),
            JobLead(user_id=2, title='别人的高分', url='u5', quick_score=95),
        ])
        db.commit()

        assert mark_above(db, 1, 60) == 3

        got = {r.url: r.status for r in db.query(JobLead).all()}
        assert got['u1'] == '待投递'
        assert got['u2'] == '待投递'
        assert got['u3'] == '新抓取'
        assert got['u4'] == '待投递'
        assert got['u6'] == '已投递'
        assert got['u5'] == '新抓取'

def test_unmark_all_only_touches_pending():
    with make_db() as db:
        db.add_all([
            JobLead(user_id=1, url='u1', title='待投1',
                    quick_score=90, status='待投递'),
            JobLead(user_id=1, url='u2', title='待投2',
                    quick_score=60, status='待投递'),
            JobLead(user_id=1, url='u3', title='已投递',
                    quick_score=80, status='已投递'),
            JobLead(user_id=1, url='u4', title='已跳过',
                    quick_score=80, status='已跳过'),
            JobLead(user_id=1, title='已投递的高分', url='u6',
                    quick_score=85, status='已投递'),
            JobLead(user_id=2, url='u5', title='别人的',
                    quick_score=80, status='待投递'),
        ])
        db.commit()

        assert unmark_all(db, 1) == 2

        got = {r.url: r.status for r in db.query(JobLead).all()}
        assert got['u1'] == '新抓取'
        assert got['u2'] == '新抓取'
        assert got['u3'] == '已投递'
        assert got['u4'] == '已跳过'
        assert got['u5'] == '待投递'


def test_delete_without_jd_is_scoped_and_keeps_applied():
    with make_db() as db:
        db.add_all([
            JobLead(user_id=1,title='未读',url='u1',jd_text=None,status='新抓取'),
            JobLead(user_id=1,title='已读',url='u2',jd_text='已经读取的岗位介绍内容，长度足够用于测试',status='新抓取'),
            JobLead(user_id=1,title='已投递未读',url='u3',jd_text=None,status='已投递'),
            JobLead(user_id=2,title='别人的未读',url='u4',jd_text=None,status='新抓取'),
        ])
        db.commit()

        assert service.delete_without_jd(db,1) == 1
        assert {row.url for row in db.query(JobLead).all()} == {'u2','u3','u4'}


def fake_ctx(monkeypatch):
    # 所有标题向量都一样：标题分都是 100，只看 JD 门槛和加分
    monkeypatch.setattr('app.services.matching_service.embed_many', lambda texts: {t: [1.0, 0.0] for t in texts})
    analysis = SimpleNamespace(skills=[], recommended_positions=[])
    targets = load_targets([{'name': 'B', 'positions': ['电商运营'], 'max_years': 3}], analysis)
    return {'analysis': analysis, 'targets': targets, 'profile': {'edu': 3, 'full': 2, 'elite': False, 'years': 2.75}}


def test_save_jd_screens(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(JobLead(user_id=1, title='电商运营助理', company='A', url='u1', tags=['本科'], quick_score=59, base_score=90))
        db.commit()
        jd = '1、统招本科及以上学历\n2、熟练使用 Python 做数据分析'
        result = service.save_jd(db, 1, [LeadJdIn(url='u1', jd_text=jd)], fake_ctx(monkeypatch))
        assert (result['updated'], result['missed']) == (1, 0)
        assert result['items'][0]['url'] == 'u1'
        assert result['items'][0]['score'] == 50
        row = db.query(JobLead).one()
        assert (row.jd_flags, row.target, row.base_score, row.quick_score) == (['要全日制本科'], 'B', 70, 50)

        # 读过 JD 的岗位，插件再传标题分也不覆盖
        assert save_leads(db, 1, [LeadIn(title='电商运营助理', company='A', url='u1', quick_score=70)])['updated'] == 0
        db.refresh(row)
        assert row.quick_score == 50


def test_save_jd_returns_stale_hr_skip(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(JobLead(user_id=1, title='电商运营助理', company='A', url='u1', tags=[], quick_score=59, base_score=80))
        db.commit()
        jd = '负责店铺运营和数据分析\n李女士\n本月活跃\n某公司 · HR'
        result = service.save_jd(db, 1, [LeadJdIn(url='u1', jd_text=jd)], fake_ctx(monkeypatch))
        assert result['items'][0]['score'] == 0
        assert result['items'][0]['skip'] is True
        assert result['items'][0]['reason'] == 'HR超过3天未活跃（本月活跃）'


def test_rescore_all(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            JobLead(user_id=1, title='电商运营助理', url='u1', tags=[], quick_score=0, jd_text='负责抖音店铺运营和数据复盘'),
            JobLead(user_id=1, title='电商运营专员', url='u2', tags=[], quick_score=0),
            JobLead(user_id=2, title='别人的岗位', url='u3', tags=[], quick_score=7),
        ])
        db.commit()
        assert service.rescore_all(db, 1, fake_ctx(monkeypatch)) == {'total': 2, 'passed': 1}
        scores = {row.url: (row.quick_score, row.target) for row in db.query(JobLead).all()}
        # 读过 JD 的按 JD 算；没读过 JD 最高 59；别人的岗位不动
        assert scores == {'u1': (74, 'B'), 'u2': (54, 'B'), 'u3': (7, None)}
        row=db.query(JobLead).filter(JobLead.url=='u1').one()
        assert row.jd_hits == ['数据分析/报表','电商平台/运营']


def test_save_leads_reports_urls_with_jd():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        save_leads(db, 1, [LeadIn(title='电商运营助理', url='u1', quick_score=70)])
        row = db.query(JobLead).one()
        row.jd_text = '负责店铺日常运营'
        db.commit()
        # 已经读过 JD 的链接回给插件，插件据此跳过、不再点开详情页
        again = save_leads(db, 1, [LeadIn(title='电商运营助理', url='u1', quick_score=70)])
        assert again['has_jd'] == ['u1']
