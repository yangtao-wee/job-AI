from types import SimpleNamespace as NS
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_current_user,get_db

client=TestClient(app)


def test_save_targets_cleans_and_saves():
    user=NS(id=7,job_targets=None)
    db=MagicMock()
    db.query.return_value.filter.return_value.first.return_value=user
    app.dependency_overrides[get_current_user]=lambda:user
    app.dependency_overrides[get_db]=lambda:db
    try:
        body={'targets':[{
            'name':' 简历A ',
            'positions':[' RPA技术支持 ','RPA技术支持','  '],
            'junior':['售前技术支持'],
            'max_years':1,
            'min_pay':7,
            'good_words':['助理'],
        }]}
        res=client.put('/targets',json=body)
        assert res.status_code==200
        saved=res.json()['targets']
        # 去空格、去重、去空行
        assert saved==[{'name':'简历A','positions':['RPA技术支持'],'junior':['售前技术支持'],'backup':[],'max_years':1,'min_pay':7,'good_words':['助理']}]
        assert user.job_targets==saved
        db.commit.assert_called_once()
        assert client.get('/targets').json()=={'targets':saved}
    finally:
        app.dependency_overrides.clear()


def test_save_targets_rejects_bad_input():
    user=NS(id=7,job_targets=None)
    app.dependency_overrides[get_current_user]=lambda:user
    app.dependency_overrides[get_db]=lambda:MagicMock()
    try:
        same_name={'targets':[{'name':'A','positions':['电商运营']},{'name':'A','positions':['RPA技术支持']}]}
        assert client.put('/targets',json=same_name).status_code==422
        blank={'targets':[{'name':'A','positions':['  ']}]}
        assert client.put('/targets',json=blank).status_code==422
        assert user.job_targets is None
    finally:
        app.dependency_overrides.clear()
