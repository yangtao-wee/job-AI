import json
from app.services.matching_service import calculate_skill_score,calculate_keyword_score,calculate_experience_score,score_role,score_pref

def test_rank():
    data=json.load(open('tests/data/match_cases.json',encoding='utf-8'))
    u=data['user']
    rows=[]
    for j in data['jobs']:

        skill=calculate_skill_score(u['skills'],j['skills']).score
        # u：【自己命名】，user的短写，代表模拟用户。
        # j：【自己命名】，job的短写，当前岗位。
        # .score：只取评分结果中的数字。
        key=calculate_keyword_score(u['skills'],j['desc']).score
        exp=calculate_experience_score(u['work'],j['duties']).score
        role=score_role(j['title'],u['roles']).score
        pref=score_pref(j['city'],j['pay'],u['city'],u['min_pay']).score
        rows.append((skill+key+exp+role+pref,j['want']))
    rows.sort(reverse=True)
        # sort(reverse=True)：从最高分排到最低分。
    assert rows==[(95,1),(45,2),(15,3)]
        # assert：【语言固定】，实际结果必须等于预期结果。
# skill：技能分。
# key：关键词分。
# exp：经历分。
# role：岗位方向分。
# pref：城市和薪资偏好分。