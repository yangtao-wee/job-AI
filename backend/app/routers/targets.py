from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from ..dependencies import get_current_user,get_db
from ..models import User
from ..schemas import JobTargets

router=APIRouter()


def clean(items:list[str],size:int=30)->list[str]:
    # 去掉首尾空格和空行，每个最多 size 字，去重但保持顺序
    return list(dict.fromkeys(s.strip()[:size] for s in items if s.strip()))


@router.get('')
def read_targets(current_user:User=Depends(get_current_user)):
    return {'targets':current_user.job_targets or []}


@router.put('')
def save_targets(
    body:JobTargets,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    targets=[]
    for t in body.targets:
        positions=clean(t.positions)
        if not positions:
            raise HTTPException(status_code=422,detail=f'方案「{t.name}」至少填一个求职方向')
        targets.append({
            'name':t.name.strip(),
            'positions':positions,
            'junior':clean(t.junior),
            'backup':clean(t.backup),
            'max_years':t.max_years,
            'min_pay':t.min_pay,
            'good_words':clean(t.good_words,10),
        })
    names=[t['name'] for t in targets]
    if not all(names) or len(set(names))!=len(names):
        raise HTTPException(status_code=422,detail='方案名字不能为空，也不能重复')
    user=db.query(User).filter(User.id==current_user.id).first()
    # 整个换成新列表，数据库才能察觉到变化
    user.job_targets=targets
    db.commit()
    return {'targets':targets}
